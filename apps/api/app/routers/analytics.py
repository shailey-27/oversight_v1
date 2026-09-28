"""
Analytics Router — Priority scores, dashboard overview, institution details
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_official_or_inspector
from app.models.models import Institution, AnomalyScore, User, Inspection
from app.services.scoring import compute_priority_score, get_risk_level, get_recommended_action

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard-overview")
async def dashboard_overview(
    current_user: User = Depends(require_official_or_inspector),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns high-level dashboard stats for the official.
    Shows all institutions with their latest priority score.
    """
    # Get all active institutions
    inst_result = await db.execute(
        select(Institution).where(Institution.is_active == True)
    )
    institutions = inst_result.scalars().all()

    # For each institution, get latest score
    institution_data = []
    high_risk = medium_risk = low_risk = 0

    for inst in institutions:
        score_result = await db.execute(
            select(AnomalyScore)
            .where(AnomalyScore.institution_id == inst.id)
            .order_by(AnomalyScore.computed_at.desc())
            .limit(1)
        )
        latest_score = score_result.scalar_one_or_none()
        score_val = latest_score.priority_score if latest_score else 0.0
        risk = get_risk_level(score_val)

        if risk == "HIGH" or risk == "CRITICAL":
            high_risk += 1
        elif risk == "MEDIUM":
            medium_risk += 1
        else:
            low_risk += 1

        institution_data.append({
            "id": inst.id,
            "name": inst.name,
            "district": inst.district,
            "state": inst.state,
            "institution_type": inst.institution_type,
            "priority_score": score_val,
            "risk_level": risk,
            "last_score_updated": latest_score.computed_at if latest_score else None,
        })

    # Sort by score descending
    institution_data.sort(key=lambda x: x["priority_score"], reverse=True)

    # Active inspections
    active_result = await db.execute(
        select(func.count(Inspection.id)).where(
            Inspection.status.in_(["scheduled", "in_progress"])
        )
    )
    active_inspections = active_result.scalar() or 0

    return {
        "total_institutions": len(institutions),
        "high_risk_count": high_risk,
        "medium_risk_count": medium_risk,
        "low_risk_count": low_risk,
        "active_inspections": active_inspections,
        "institutions": institution_data,
    }


@router.get("/priority-score/{institution_id}")
async def get_priority_score(
    institution_id: str,
    current_user: User = Depends(require_official_or_inspector),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the latest explainable priority score for one institution,
    including the full factor breakdown and score history.
    """
    inst_result = await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    institution = inst_result.scalar_one_or_none()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found.")

    # Latest score
    score_result = await db.execute(
        select(AnomalyScore)
        .where(AnomalyScore.institution_id == institution_id)
        .order_by(AnomalyScore.computed_at.desc())
        .limit(1)
    )
    latest = score_result.scalar_one_or_none()

    if not latest:
        return {
            "institution_id": institution_id,
            "institution_name": institution.name,
            "priority_score": 0.0,
            "risk_level": "LOW",
            "message": "No score computed yet. Score will update within the next cycle.",
            "factors": [],
            "history": [],
        }

    # Score history (last 14 records)
    history_result = await db.execute(
        select(AnomalyScore)
        .where(AnomalyScore.institution_id == institution_id)
        .order_by(AnomalyScore.computed_at.desc())
        .limit(14)
    )
    history = history_result.scalars().all()

    # Format factors for frontend consumption
    factors_list = [
        {
            "key": key,
            "label": _factor_display_names.get(key, key),
            "raw_score": data["raw_score"],
            "weight": data["weight"],
            "contribution": round(data["raw_score"] * data["weight"] * 10, 2),
            "explanation": data["label"],
        }
        for key, data in (latest.factors or {}).items()
    ]

    risk = get_risk_level(latest.priority_score)

    return {
        "institution_id": institution_id,
        "institution_name": institution.name,
        "district": institution.district,
        "state": institution.state,
        "priority_score": latest.priority_score,
        "risk_level": risk,
        "computed_at": latest.computed_at,
        "score_version": latest.score_version,
        "recommended_action": get_recommended_action(latest.priority_score),
        "factors": factors_list,
        "history": [
            {"date": s.computed_at.date().isoformat(), "score": s.priority_score}
            for s in reversed(history)
        ],
    }


@router.post("/compute-score/{institution_id}")
async def trigger_score_computation(
    institution_id: str,
    current_user: User = Depends(require_official_or_inspector),
    db: AsyncSession = Depends(get_db),
):
    """
    Manually trigger a fresh score computation for one institution.
    Background scheduler does this automatically every 4 hours.
    """
    inst_result = await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    if not inst_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Institution not found.")

    score = await compute_priority_score(db, institution_id)
    return {
        "message": "Score recomputed successfully.",
        "priority_score": score.priority_score,
        "risk_level": get_risk_level(score.priority_score),
        "factors": score.factors,
    }


_factor_display_names = {
    "attendance_vs_reported": "Attendance vs Reported",
    "cctv_vs_checkins": "CCTV Occupancy vs App Check-ins",
    "invoice_anomaly": "Invoice Anomaly Flags",
    "historical_pattern": "Historical Risk Pattern",
    "call_compliance": "Surprise Call Compliance",
}
