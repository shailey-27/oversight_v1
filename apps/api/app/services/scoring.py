"""
Rule-Based Anomaly Scoring Engine — v1
Computes an explainable Inspection Priority Score (0–10) for each institution.
No ML required. All factors are transparent and auditable.

Score Formula:
  Priority Score = Σ (factor_raw_score × weight) × 10

Factors:
  1. Attendance vs Reported      weight: 0.30
  2. CCTV Occupancy vs Check-ins weight: 0.30
  3. Invoice Anomaly             weight: 0.20
  4. Historical Pattern          weight: 0.10
  5. Call Compliance             weight: 0.10
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import (
    AttendanceRecord, OccupancyLog, Invoice,
    AnomalyScore, Inspection, VideoCallInspection, Institution
)


# ── Risk Band Labels ─────────────────────────────────────────────────────────

def get_risk_level(score: float) -> str:
    if score < 3.0:
        return "LOW"
    elif score < 6.0:
        return "MEDIUM"
    elif score < 8.0:
        return "HIGH"
    else:
        return "CRITICAL"


def get_recommended_action(score: float) -> str:
    if score < 3.0:
        return "Routine monitoring. Next scheduled inspection as planned."
    elif score < 6.0:
        return "Consider initiating a surprise video call verification."
    elif score < 8.0:
        return "Assign a physical inspection. High anomaly signals detected."
    else:
        return "CRITICAL: Immediate action required. Consider temporary fund disbursement review."


# ── Factor 1: Attendance vs Reported ─────────────────────────────────────────

async def factor_attendance_vs_reported(
    db: AsyncSession, institution_id: str, window_days: int = 7
) -> tuple[float, str]:
    """
    Compares app check-ins vs. what NGO claims in project beneficiary count.
    For the prototype, we use enrolled beneficiary count as the 'reported' figure.
    """
    since = datetime.now(timezone.utc) - timedelta(days=window_days)

    # Count distinct check-ins in window
    result = await db.execute(
        select(func.count(AttendanceRecord.id)).where(
            and_(
                AttendanceRecord.institution_id == institution_id,
                AttendanceRecord.check_in_time >= since,
                AttendanceRecord.geo_validation_status == "valid",
            )
        )
    )
    actual_checkins = result.scalar() or 0

    # Get institution to find enrolled beneficiaries
    from app.models.models import Beneficiary
    ben_result = await db.execute(
        select(func.count()).where(
            and_(
                Beneficiary.institution_id == institution_id,
                Beneficiary.status == "active",
            )
        )
    )
    enrolled_count = ben_result.scalar() or 0

    if enrolled_count == 0:
        return 0.0, "No beneficiaries enrolled — cannot assess attendance gap."

    # Expected check-ins over window = enrolled × days × 0.8 (80% expected attendance)
    expected = enrolled_count * window_days * 0.8
    if expected == 0:
        return 0.0, "Cannot compute expected attendance."

    gap_ratio = max(0, (expected - actual_checkins) / expected)

    # Threshold → score
    if gap_ratio < 0.10:
        raw = 0.0
    elif gap_ratio < 0.25:
        raw = 0.4
    elif gap_ratio < 0.40:
        raw = 0.7
    else:
        raw = 1.0

    label = (
        f"App check-ins ({actual_checkins}) are {gap_ratio*100:.0f}% below "
        f"expected ({expected:.0f}) over last {window_days} days."
    )
    return raw, label


# ── Factor 2: CCTV Occupancy vs Check-ins ────────────────────────────────────

async def factor_cctv_vs_checkins(
    db: AsyncSession, institution_id: str, window_days: int = 7
) -> tuple[float, str]:
    """
    Compares average CCTV occupancy count vs average daily app check-ins.
    Only applied when confidence_score > 0.6 to avoid false positives.
    """
    since = datetime.now(timezone.utc) - timedelta(days=window_days)

    # Average CCTV count (high confidence only)
    cctv_result = await db.execute(
        select(func.avg(OccupancyLog.estimated_count)).where(
            and_(
                OccupancyLog.institution_id == institution_id,
                OccupancyLog.sampled_at >= since,
                OccupancyLog.confidence_score >= 0.6,
            )
        )
    )
    avg_cctv = float(cctv_result.scalar() or 0)

    # Average daily check-ins
    checkin_result = await db.execute(
        select(func.count(AttendanceRecord.id)).where(
            and_(
                AttendanceRecord.institution_id == institution_id,
                AttendanceRecord.check_in_time >= since,
                AttendanceRecord.geo_validation_status == "valid",
            )
        )
    )
    total_checkins = checkin_result.scalar() or 0
    avg_daily_checkins = total_checkins / window_days

    # Check if CCTV data exists at all
    cctv_count_result = await db.execute(
        select(func.count(OccupancyLog.id)).where(
            and_(
                OccupancyLog.institution_id == institution_id,
                OccupancyLog.sampled_at >= since,
            )
        )
    )
    cctv_sample_count = cctv_count_result.scalar() or 0

    if cctv_sample_count < 3:
        return 0.0, f"Insufficient CCTV data ({cctv_sample_count} samples). Skipping CCTV factor."

    if avg_daily_checkins == 0:
        return 0.3, "No app check-ins recorded this period. CCTV data present."

    gap_ratio = max(0, (avg_daily_checkins - avg_cctv) / avg_daily_checkins)

    if gap_ratio < 0.15:
        raw = 0.0
    elif gap_ratio < 0.30:
        raw = 0.4
    elif gap_ratio < 0.50:
        raw = 0.7
    else:
        raw = 1.0

    label = (
        f"CCTV avg occupancy ({avg_cctv:.1f}) is {gap_ratio*100:.0f}% below "
        f"app check-ins ({avg_daily_checkins:.1f}/day) over last {window_days} days."
    )
    return raw, label


# ── Factor 3: Invoice Anomaly ─────────────────────────────────────────────────

async def factor_invoice_anomaly(
    db: AsyncSession, institution_id: str
) -> tuple[float, str]:
    """
    Checks for flagged invoices and known anomaly patterns.
    Sub-rules:
      I-1: Duplicate document hash
      I-2: Duplicate invoice number (same vendor)
      I-3: Amount spike (>2.5x category mean)
      I-4: Split invoice pattern (3+ from same vendor in 7 days below ₹50k)
    """
    # Count currently flagged invoices
    flagged_result = await db.execute(
        select(func.count(Invoice.id)).where(
            and_(
                Invoice.institution_id == institution_id,
                Invoice.status == "flagged",
            )
        )
    )
    flagged_count = flagged_result.scalar() or 0

    if flagged_count == 0:
        return 0.0, "No invoice anomalies detected."
    elif flagged_count == 1:
        raw = 0.3
    elif flagged_count == 2:
        raw = 0.7
    else:
        raw = 1.0

    label = f"{flagged_count} invoice(s) currently flagged for anomalies pending review."
    return raw, label


# ── Factor 4: Historical Pattern ──────────────────────────────────────────────

async def factor_historical_pattern(
    db: AsyncSession, institution_id: str
) -> tuple[float, str]:
    """
    Counts how many of the past 4 weeks had a priority score > 6.
    Persistent high scores indicate systemic issues, not one-off events.
    """
    four_weeks_ago = datetime.now(timezone.utc) - timedelta(weeks=4)

    result = await db.execute(
        select(AnomalyScore).where(
            and_(
                AnomalyScore.institution_id == institution_id,
                AnomalyScore.computed_at >= four_weeks_ago,
                AnomalyScore.priority_score > 6.0,
            )
        ).order_by(AnomalyScore.computed_at.desc()).limit(20)
    )
    high_score_records = result.scalars().all()

    # Count distinct weeks with high scores
    weeks_with_high_score = len(set(
        r.computed_at.isocalendar()[1] for r in high_score_records
    ))

    if weeks_with_high_score == 0:
        raw = 0.0
        label = "No persistent high-risk pattern in the last 4 weeks."
    elif weeks_with_high_score == 1:
        raw = 0.3
        label = "High risk score detected in 1 of the last 4 weeks."
    elif weeks_with_high_score == 2:
        raw = 0.6
        label = "High risk scores in 2 of the last 4 weeks — emerging pattern."
    else:
        raw = 1.0
        label = f"High risk scores in {weeks_with_high_score} of the last 4 weeks — persistent pattern."

    return raw, label


# ── Factor 5: Call/Inspection Compliance ──────────────────────────────────────

async def factor_call_compliance(
    db: AsyncSession, institution_id: str
) -> tuple[float, str]:
    """
    Tracks no-shows on surprise video calls in the last 30 days.
    """
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)

    # Find all video calls for this institution in the window
    result = await db.execute(
        select(VideoCallInspection)
        .join(Inspection, Inspection.id == VideoCallInspection.inspection_id)
        .where(
            and_(
                Inspection.institution_id == institution_id,
                VideoCallInspection.initiated_at >= thirty_days_ago,
            )
        )
    )
    calls = result.scalars().all()

    total_calls = len(calls)
    no_shows = sum(1 for c in calls if c.no_show_recorded)

    if total_calls == 0:
        return 0.0, "No surprise calls conducted in the last 30 days."

    if no_shows == 0:
        raw = 0.0
        label = f"All {total_calls} surprise call(s) attended in the last 30 days."
    elif no_shows == 1:
        raw = 0.5
        label = f"1 of {total_calls} surprise call(s) was a no-show."
    else:
        raw = 1.0
        label = f"{no_shows} of {total_calls} surprise calls were no-shows — serious compliance issue."

    return raw, label


# ── Master Score Computation ──────────────────────────────────────────────────

WEIGHTS = {
    "attendance_vs_reported": 0.30,
    "cctv_vs_checkins": 0.30,
    "invoice_anomaly": 0.20,
    "historical_pattern": 0.10,
    "call_compliance": 0.10,
}


async def compute_priority_score(
    db: AsyncSession,
    institution_id: str,
    window_days: int = 7,
) -> AnomalyScore:
    """
    Main entry point. Computes the full Inspection Priority Score for an institution.
    Persists result to anomaly_scores table and returns the new record.
    """

    # Compute all factors in parallel-ish (sequential for simplicity in v1)
    att_score, att_label   = await factor_attendance_vs_reported(db, institution_id, window_days)
    cctv_score, cctv_label = await factor_cctv_vs_checkins(db, institution_id, window_days)
    inv_score, inv_label   = await factor_invoice_anomaly(db, institution_id)
    hist_score, hist_label = await factor_historical_pattern(db, institution_id)
    call_score, call_label = await factor_call_compliance(db, institution_id)

    # Weighted sum → scale to 0–10
    weighted_sum = (
        att_score   * WEIGHTS["attendance_vs_reported"] +
        cctv_score  * WEIGHTS["cctv_vs_checkins"] +
        inv_score   * WEIGHTS["invoice_anomaly"] +
        hist_score  * WEIGHTS["historical_pattern"] +
        call_score  * WEIGHTS["call_compliance"]
    )
    priority_score = round(weighted_sum * 10, 2)

    factors = {
        "attendance_vs_reported": {
            "weight": WEIGHTS["attendance_vs_reported"],
            "raw_score": att_score,
            "label": att_label,
        },
        "cctv_vs_checkins": {
            "weight": WEIGHTS["cctv_vs_checkins"],
            "raw_score": cctv_score,
            "label": cctv_label,
        },
        "invoice_anomaly": {
            "weight": WEIGHTS["invoice_anomaly"],
            "raw_score": inv_score,
            "label": inv_label,
        },
        "historical_pattern": {
            "weight": WEIGHTS["historical_pattern"],
            "raw_score": hist_score,
            "label": hist_label,
        },
        "call_compliance": {
            "weight": WEIGHTS["call_compliance"],
            "raw_score": call_score,
            "label": call_label,
        },
    }

    score_record = AnomalyScore(
        institution_id=institution_id,
        priority_score=priority_score,
        factors=factors,
        score_version="v1_rule_based",
    )
    db.add(score_record)
    await db.flush()  # get ID without committing yet
    return score_record
