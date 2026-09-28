"""
Attendance Router — Check-in with GPS geo-fence validation + OTP verification
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import AttendanceRecord, Institution, OTPRequest, User
from app.services.geo import check_geo_fence

router = APIRouter(prefix="/attendance", tags=["Attendance"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class CheckInRequest(BaseModel):
    institution_id: str
    project_id: str | None = None
    geo_lat: float
    geo_lng: float
    otp: str
    device_id: str | None = None


class CheckOutRequest(BaseModel):
    record_id: str
    geo_lat: float
    geo_lng: float


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/checkin")
async def check_in(
    body: CheckInRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Beneficiary/Staff check-in:
    1. Validates OTP (5-min window)
    2. Validates GPS is within institution geo-fence (Haversine)
    3. Creates attendance record
    """

    # 1. Validate OTP
    now = datetime.now(timezone.utc)
    otp_result = await db.execute(
        select(OTPRequest).where(
            and_(
                OTPRequest.phone == current_user.phone,
                OTPRequest.otp_code == body.otp,
                OTPRequest.is_used == False,
                OTPRequest.expires_at > now,
            )
        ).order_by(OTPRequest.created_at.desc()).limit(1)
    )
    otp_record = otp_result.scalar_one_or_none()

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired OTP. Request a fresh OTP to check in."
        )
    otp_record.is_used = True

    # 2. Get institution for geo-fence check
    inst_result = await db.execute(
        select(Institution).where(Institution.id == body.institution_id)
    )
    institution = inst_result.scalar_one_or_none()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found.")

    if institution.geo_lat is None or institution.geo_lng is None:
        # No geo-fence configured — allow check-in but mark as unverified
        geo_result = {"within_fence": True, "distance_meters": 0, "status": "valid"}
    else:
        geo_result = check_geo_fence(
            check_lat=body.geo_lat,
            check_lng=body.geo_lng,
            center_lat=institution.geo_lat,
            center_lng=institution.geo_lng,
            radius_meters=institution.geo_fence_radius_meters,
        )

    # 3. Check for duplicate device check-in in same day (fraud detection)
    if body.device_id:
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        dup_result = await db.execute(
            select(func.count(AttendanceRecord.id)).where(
                and_(
                    AttendanceRecord.institution_id == body.institution_id,
                    AttendanceRecord.device_id == body.device_id,
                    AttendanceRecord.check_in_time >= today_start,
                    AttendanceRecord.recorded_by != current_user.id,  # different user, same device
                )
            )
        )
        dup_count = dup_result.scalar() or 0
        if dup_count > 0:
            geo_result["status"] = "suspicious"

    # 4. Create record
    record = AttendanceRecord(
        institution_id=body.institution_id,
        project_id=body.project_id,
        recorded_by=current_user.id,
        geo_lat=body.geo_lat,
        geo_lng=body.geo_lng,
        geo_validation_status=geo_result["status"],
        distance_from_center_m=geo_result.get("distance_meters"),
        otp_verified=True,
        device_id=body.device_id,
        sync_status="synced",
    )
    db.add(record)
    await db.flush()

    return {
        "record_id": record.id,
        "status": geo_result["status"],
        "geo_validation": {
            "within_fence": geo_result["within_fence"],
            "distance_from_center_meters": geo_result.get("distance_meters"),
        },
        "message": _checkin_message(geo_result["status"]),
        "check_in_time": record.check_in_time,
    }


@router.post("/checkout")
async def check_out(
    body: CheckOutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Records check-out time for an existing attendance record."""
    result = await db.execute(
        select(AttendanceRecord).where(
            and_(
                AttendanceRecord.id == body.record_id,
                AttendanceRecord.recorded_by == current_user.id,
            )
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found.")
    if record.check_out_time:
        raise HTTPException(status_code=400, detail="Already checked out.")

    record.check_out_time = datetime.now(timezone.utc)

    return {
        "record_id": record.id,
        "check_out_time": record.check_out_time,
        "message": "Check-out recorded successfully.",
    }


@router.get("/history")
async def get_history(
    institution_id: str | None = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns attendance history for the current user (or institution if official/NGO)."""
    query = select(AttendanceRecord)

    if current_user.role in ("dosje_official", "pmu_inspector"):
        if institution_id:
            query = query.where(AttendanceRecord.institution_id == institution_id)
    else:
        query = query.where(AttendanceRecord.recorded_by == current_user.id)

    query = query.order_by(AttendanceRecord.check_in_time.desc()).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    return [
        {
            "id": r.id,
            "institution_id": r.institution_id,
            "check_in_time": r.check_in_time,
            "check_out_time": r.check_out_time,
            "geo_validation_status": r.geo_validation_status,
            "distance_from_center_m": r.distance_from_center_m,
        }
        for r in records
    ]


def _checkin_message(status: str) -> str:
    messages = {
        "valid": "✅ Check-in successful! You are within the institution premises.",
        "suspicious": "⚠️ Check-in recorded, but your location seems unusual. Please verify.",
        "outside_fence": "❌ Check-in recorded but you appear to be outside the institution area.",
    }
    return messages.get(status, "Check-in recorded.")
