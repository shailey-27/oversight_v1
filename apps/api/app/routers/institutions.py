"""
Institutions Router — CRUD for NGOs/Institutions
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user, require_official_or_inspector
from app.models.models import Institution, User, OccupancyLog
from app.routers.realtime import manager

router = APIRouter(prefix="/institutions", tags=["Institutions"])

class OccupancyRequest(BaseModel):
    estimated_count: int
    confidence_score: float = 1.0
    method: str = "opencv_headcount"

@router.post("/{institution_id}/occupancy")
async def log_occupancy(
    institution_id: str,
    body: OccupancyRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint for the YOLOv8 CCTV Python worker to submit live headcount data.
    """
    # Verify institution exists
    result = await db.execute(select(Institution).where(Institution.id == institution_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Institution not found")

    log = OccupancyLog(
        institution_id=institution_id,
        estimated_count=body.estimated_count,
        confidence_score=body.confidence_score,
        method=body.method,
    )
    db.add(log)
    await db.commit()

    # Broadcast to all connected clients
    await manager.broadcast_to_officials({
        "type": "CCTV_UPDATE",
        "institution_id": institution_id,
        "estimated_count": body.estimated_count,
        "timestamp": log.sampled_at.isoformat() if log.sampled_at else None
    }, db)

    return {"status": "success", "count": body.estimated_count}



class CreateInstitutionRequest(BaseModel):
    name: str
    registration_number: str
    institution_type: str = "ngo"
    address: str | None = None
    geo_lat: float | None = None
    geo_lng: float | None = None
    geo_fence_radius_meters: int = 100
    district: str | None = None
    state: str | None = None


@router.get("/")
async def list_institutions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Institution).where(Institution.is_active == True)
    )
    institutions = result.scalars().all()
    return [
        {
            "id": i.id,
            "name": i.name,
            "registration_number": i.registration_number,
            "institution_type": i.institution_type,
            "district": i.district,
            "state": i.state,
            "geo_lat": i.geo_lat,
            "geo_lng": i.geo_lng,
        }
        for i in institutions
    ]


@router.get("/{institution_id}")
async def get_institution(
    institution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Institution).where(Institution.id == institution_id)
    )
    institution = result.scalar_one_or_none()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found.")
    return institution


@router.post("/")
async def create_institution(
    body: CreateInstitutionRequest,
    current_user: User = Depends(require_official_or_inspector),
    db: AsyncSession = Depends(get_db),
):
    institution = Institution(
        name=body.name,
        registration_number=body.registration_number,
        institution_type=body.institution_type,
        address=body.address,
        geo_lat=body.geo_lat,
        geo_lng=body.geo_lng,
        geo_fence_radius_meters=body.geo_fence_radius_meters,
        district=body.district,
        state=body.state,
        admin_user_id=current_user.id,
    )
    db.add(institution)
    await db.flush()
    return {"id": institution.id, "name": institution.name, "message": "Institution created."}
