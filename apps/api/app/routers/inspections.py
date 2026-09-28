"""
Inspections Router — Create inspections, assign inspectors, submit checklists
"""

import math
import random
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_official_or_inspector
from app.models.models import (
    Inspection, Institution, User, AnomalyScore,
    ChecklistItem, ComplianceHistory, AuditLog
)
from app.services.geo import haversine_distance
from app.services.scoring import get_risk_level

router = APIRouter(prefix="/inspections", tags=["Inspections"])

MAX_CONCURRENT_INSPECTIONS = 3
MAX_DISTANCE_KM = 300


# ── Schemas ───────────────────────────────────────────────────────────────────

class AssignInspectionRequest(BaseModel):
    institution_id: str
    inspection_type: str = "physical"  # physical | surprise_video | routine
    urgency: str = "within_48h"         # immediate | within_48h
    override_inspector_id: str | None = None
    trigger_reason: str | None = None


class ChecklistResponseItem(BaseModel):
    local_temp_id: str | None = None
    category: str | None = None
    question: str
    response: str  # yes | no | partial | na
    remarks: str | None = None
    geo_lat: float | None = None
    geo_lng: float | None = None
    evidence_urls: list[str] | None = None


class SubmitInspectionRequest(BaseModel):
    checklist_responses: list[ChecklistResponseItem]
    submitted_offline: bool = False
    offline_captured_at: str | None = None


# ── Inspector Assignment Algorithm ────────────────────────────────────────────

async def auto_assign_inspector(
    db: AsyncSession,
    institution: Institution,
    urgency: str,
) -> tuple[User | None, str, bool]:
    """
    Returns: (assigned_inspector, rationale_text, constraints_relaxed)

    Algorithm Steps:
    1. ELIGIBILITY: not recent inspector for this institution, not same district,
       active_inspections < MAX_CONCURRENT
    2. LOCATION: Haversine distance score
    3. WORKLOAD: fewer active inspections = higher score
    4. RANDOM JITTER: 20% weight to prevent gaming
    5. SELECT TOP candidate
    """

    # Get all active inspectors
    result = await db.execute(
        select(User).where(
            and_(User.role == "pmu_inspector", User.is_active == True)
        )
    )
    all_inspectors = result.scalars().all()

    if not all_inspectors:
        return None, "No inspectors available in the system.", False

    # Get recent inspectors for this institution (last 2 inspections)
    recent_result = await db.execute(
        select(Inspection.assigned_inspector_id)
        .where(Inspection.institution_id == institution.id)
        .order_by(Inspection.created_at.desc())
        .limit(2)
    )
    recent_inspector_ids = {row[0] for row in recent_result.all() if row[0]}

    # Count active inspections per inspector
    active_counts = {}
    for inspector in all_inspectors:
        count_result = await db.execute(
            select(func.count(Inspection.id)).where(
                and_(
                    Inspection.assigned_inspector_id == inspector.id,
                    Inspection.status.in_(["scheduled", "in_progress"]),
                )
            )
        )
        active_counts[inspector.id] = count_result.scalar() or 0

    # STEP 1: Eligibility filter (hard rules)
    eligible = []
    for inspector in all_inspectors:
        if inspector.id in recent_inspector_ids:
            continue  # conflict of interest
        if inspector.district == institution.district and urgency != "immediate":
            continue  # geographic conflict (relaxed for immediate)
        if active_counts.get(inspector.id, 0) >= MAX_CONCURRENT_INSPECTIONS:
            continue  # workload exceeded
        eligible.append(inspector)

    constraints_relaxed = False
    if not eligible:
        # Relax same-district constraint for urgency
        eligible = [
            i for i in all_inspectors
            if active_counts.get(i.id, 0) < MAX_CONCURRENT_INSPECTIONS
            and i.id not in recent_inspector_ids
        ]
        constraints_relaxed = True

    if not eligible:
        return None, "No eligible inspector found. All inspectors are at capacity or have conflicts.", False

    # STEP 2–4: Score each eligible inspector
    inst_lat = institution.geo_lat or 0
    inst_lng = institution.geo_lng or 0

    scored = []
    for inspector in eligible:
        insp_lat = inspector.geo_lat or inst_lat  # fallback: same location
        insp_lng = inspector.geo_lng or inst_lng

        dist_km = haversine_distance(insp_lat, insp_lng, inst_lat, inst_lng) / 1000
        travel_score = max(0.0, 1.0 - (dist_km / MAX_DISTANCE_KM))

        active = active_counts.get(inspector.id, 0)
        workload_score = 1.0 - (active / MAX_CONCURRENT_INSPECTIONS)

        jitter = random.uniform(0, 1)
        composite = (0.5 * travel_score) + (0.3 * workload_score) + (0.2 * jitter)

        scored.append((composite, dist_km, active, inspector))

    # STEP 5: Pick highest scorer
    scored.sort(key=lambda x: x[0], reverse=True)
    composite_score, dist_km, active_count, assigned = scored[0]

    rationale = (
        f"Auto-assigned to {assigned.full_name} (District: {assigned.district or 'N/A'}). "
        f"Distance: {dist_km:.0f} km. "
        f"Active inspections: {active_count}/{MAX_CONCURRENT_INSPECTIONS}. "
        f"No prior connection to this institution."
    )
    if constraints_relaxed:
        rationale += " ⚠️ Geographic conflict constraint relaxed due to urgency."

    return assigned, rationale, constraints_relaxed


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/assign")
async def assign_inspection(
    body: AssignInspectionRequest,
    current_user: User = Depends(require_official_or_inspector),
    db: AsyncSession = Depends(get_db),
):
    """Create and auto-assign an inspection to an inspector."""
    # Get institution
    inst_result = await db.execute(
        select(Institution).where(Institution.id == body.institution_id)
    )
    institution = inst_result.scalar_one_or_none()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found.")

    # Get latest anomaly score
    score_result = await db.execute(
        select(AnomalyScore)
        .where(AnomalyScore.institution_id == body.institution_id)
        .order_by(AnomalyScore.computed_at.desc())
        .limit(1)
    )
    latest_score = score_result.scalar_one_or_none()

    # Determine inspector
    if body.override_inspector_id:
        insp_result = await db.execute(
            select(User).where(User.id == body.override_inspector_id)
        )
        assigned_inspector = insp_result.scalar_one_or_none()
        rationale = f"Manually assigned by {current_user.full_name}."
        constraints_relaxed = False
        method = "manual"
    else:
        assigned_inspector, rationale, constraints_relaxed = await auto_assign_inspector(
            db, institution, body.urgency
        )
        method = "auto"

    # Scheduled time
    if body.urgency == "immediate":
        scheduled_for = datetime.now(timezone.utc) + timedelta(hours=2)
    else:
        scheduled_for = datetime.now(timezone.utc) + timedelta(hours=48)

    inspection = Inspection(
        institution_id=body.institution_id,
        inspection_type=body.inspection_type,
        triggered_by=current_user.id,
        trigger_reason=body.trigger_reason,
        anomaly_score_id=latest_score.id if latest_score else None,
        assigned_inspector_id=assigned_inspector.id if assigned_inspector else None,
        assignment_method=method,
        assignment_rationale=rationale,
        scheduled_for=scheduled_for,
        status="scheduled",
    )
    db.add(inspection)

    # Compliance history entry
    compliance_entry = ComplianceHistory(
        institution_id=body.institution_id,
        event_type="inspection_completed" if method == "manual" else "score_spike",
        summary=f"Inspection ({body.inspection_type}) assigned. Score: {latest_score.priority_score if latest_score else 'N/A'}",
        reference_id=inspection.id,
        recorded_by=current_user.id,
        is_adverse=False,
    )
    db.add(compliance_entry)

    # Audit log
    audit = AuditLog(
        user_id=current_user.id,
        action="inspector_assigned",
        target_entity="inspections",
        extra={
            "institution_id": body.institution_id,
            "inspector_id": assigned_inspector.id if assigned_inspector else None,
            "method": method,
            "constraints_relaxed": constraints_relaxed,
        },
    )
    db.add(audit)
    await db.flush()

    return {
        "inspection_id": inspection.id,
        "institution_name": institution.name,
        "inspection_type": body.inspection_type,
        "status": "scheduled",
        "scheduled_for": scheduled_for,
        "assigned_inspector": {
            "id": assigned_inspector.id,
            "name": assigned_inspector.full_name,
            "district": assigned_inspector.district,
        } if assigned_inspector else None,
        "assignment_method": method,
        "assignment_rationale": rationale,
        "constraints_relaxed": constraints_relaxed,
    }


@router.get("/my-inspections")
async def my_inspections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns inspections assigned to the current inspector (or all for officials)."""
    if current_user.role == "pmu_inspector":
        query = select(Inspection).where(
            Inspection.assigned_inspector_id == current_user.id
        )
    else:
        query = select(Inspection)

    query = query.order_by(Inspection.created_at.desc()).limit(50)
    result = await db.execute(query)
    inspections = result.scalars().all()

    return [
        {
            "id": i.id,
            "institution_id": i.institution_id,
            "inspection_type": i.inspection_type,
            "status": i.status,
            "scheduled_for": i.scheduled_for,
            "created_at": i.created_at,
            "trigger_reason": i.trigger_reason,
        }
        for i in inspections
    ]


@router.post("/{inspection_id}/submit")
async def submit_inspection(
    inspection_id: str,
    body: SubmitInspectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Inspector submits completed checklist. Supports offline-captured data."""
    result = await db.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    )
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    if inspection.status in ("submitted", "reviewed", "closed"):
        raise HTTPException(status_code=400, detail="Inspection already submitted or closed.")

    # Save all checklist responses
    for item in body.checklist_responses:
        checklist_item = ChecklistItem(
            inspection_id=inspection_id,
            category=item.category,
            question=item.question,
            response=item.response,
            remarks=item.remarks,
            geo_lat=item.geo_lat,
            geo_lng=item.geo_lng,
            evidence_urls=item.evidence_urls or [],
            captured_offline=body.submitted_offline,
            local_temp_id=item.local_temp_id,
        )
        db.add(checklist_item)

    inspection.status = "submitted"
    inspection.completed_at = datetime.now(timezone.utc)

    # Compliance history
    compliance = ComplianceHistory(
        institution_id=inspection.institution_id,
        event_type="inspection_completed",
        summary=f"Inspection report submitted by {current_user.full_name}. {len(body.checklist_responses)} checklist items.",
        reference_id=inspection_id,
        recorded_by=current_user.id,
        is_adverse=False,
    )
    db.add(compliance)
    await db.flush()

    return {
        "inspection_id": inspection_id,
        "status": "submitted",
        "synced_count": len(body.checklist_responses),
        "submitted_at": inspection.completed_at,
        "message": "Inspection report submitted successfully.",
    }


@router.get("/{inspection_id}")
async def get_inspection(
    inspection_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full inspection details including checklist items."""
    result = await db.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    )
    inspection = result.scalar_one_or_none()
    if not inspection:
        raise HTTPException(status_code=404, detail="Inspection not found.")

    items_result = await db.execute(
        select(ChecklistItem).where(ChecklistItem.inspection_id == inspection_id)
    )
    items = items_result.scalars().all()

    return {
        "id": inspection.id,
        "institution_id": inspection.institution_id,
        "inspection_type": inspection.inspection_type,
        "status": inspection.status,
        "scheduled_for": inspection.scheduled_for,
        "trigger_reason": inspection.trigger_reason,
        "assignment_rationale": inspection.assignment_rationale,
        "completed_at": inspection.completed_at,
        "checklist_items": [
            {
                "id": item.id,
                "category": item.category,
                "question": item.question,
                "response": item.response,
                "remarks": item.remarks,
                "evidence_urls": item.evidence_urls,
            }
            for item in items
        ],
    }
