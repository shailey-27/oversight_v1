"""
Auth Router — Phone OTP Login + JWT tokens
Demo mode: OTP is returned in the API response (no SMS gateway needed for hackathon)
Production: integrate MSG91 or Fast2SMS
"""

import random
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.security import (
    create_access_token, create_refresh_token,
    decode_token, get_current_user
)
from app.models.models import User, OTPRequest, AuditLog

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class SendOTPRequest(BaseModel):
    phone: str  # e.g. "9876543210"


class VerifyOTPRequest(BaseModel):
    phone: str
    otp: str


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    phone: str
    full_name: str
    role: str  # dosje_official | pmu_inspector | ngo_admin | beneficiary
    state: str | None = None
    district: str | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


async def log_action(db: AsyncSession, action: str, user_id: str | None, request: Request, extra: dict = None):
    log = AuditLog(
        user_id=user_id,
        action=action,
        ip_address=request.client.host if request.client else "unknown",
        extra=extra or {},
    )
    db.add(log)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/send-otp")
async def send_otp(body: SendOTPRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Step 1 of login: Send OTP to phone number.
    Demo mode: OTP returned in response body (no SMS needed).
    """
    phone = body.phone.strip()
    if len(phone) != 10 or not phone.isdigit():
        raise HTTPException(status_code=400, detail="Enter a valid 10-digit phone number.")

    otp_code = generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

    # Find user if exists
    user_result = await db.execute(select(User).where(User.phone == phone))
    user = user_result.scalar_one_or_none()

    otp_record = OTPRequest(
        phone=phone,
        otp_code=otp_code,
        expires_at=expires_at,
        user_id=user.id if user else None,
    )
    db.add(otp_record)

    await log_action(db, "send_otp", user.id if user else None, request, {"phone_last4": phone[-4:]})

    # In production: send SMS via MSG91 here
    # await sms_service.send(phone, f"Your OVERSIGHT OTP is {otp_code}. Valid for 5 minutes.")

    response = {
        "message": f"OTP sent to ****{phone[-4:]}",
        "expires_in_seconds": settings.OTP_EXPIRE_MINUTES * 60,
        "user_exists": user is not None,
    }

    # Demo mode: include OTP in response so you can test without SMS gateway
    if settings.DEMO_MODE:
        response["demo_otp"] = otp_code

    return response


@router.post("/verify-otp")
async def verify_otp(body: VerifyOTPRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Step 2 of login: Verify OTP → return JWT access + refresh tokens.
    If user doesn't exist yet, returns needs_registration=True.
    """
    phone = body.phone.strip()
    now = datetime.now(timezone.utc)

    # Find most recent unused, valid OTP for this phone
    result = await db.execute(
        select(OTPRequest).where(
            and_(
                OTPRequest.phone == phone,
                OTPRequest.otp_code == body.otp,
                OTPRequest.is_used == False,
                OTPRequest.expires_at > now,
            )
        ).order_by(OTPRequest.created_at.desc()).limit(1)
    )
    otp_record = result.scalar_one_or_none()

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP. Please request a new one.")

    # Mark OTP as used
    otp_record.is_used = True

    # Find user
    user_result = await db.execute(select(User).where(User.phone == phone))
    user = user_result.scalar_one_or_none()

    if not user:
        return {
            "needs_registration": True,
            "phone": phone,
            "message": "Phone verified. Complete registration to continue.",
        }

    # Update last login
    user.last_login = now

    await log_action(db, "login_success", user.id, request)

    token_data = {"sub": user.id, "role": user.role, "phone": phone}

    return {
        "needs_registration": False,
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "token_type": "Bearer",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role,
            "district": user.district,
            "state": user.state,
        },
    }


@router.post("/register")
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """
    Complete registration after OTP verification for new users.
    Called when verify-otp returns needs_registration=True.
    """
    VALID_ROLES = {"dosje_official", "pmu_inspector", "ngo_admin", "beneficiary"}
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {VALID_ROLES}")

    # Check if phone already registered
    existing = await db.execute(select(User).where(User.phone == body.phone))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Phone number already registered.")

    user = User(
        full_name=body.full_name,
        phone=body.phone,
        role=body.role,
        state=body.state,
        district=body.district,
    )
    db.add(user)
    await db.flush()

    await log_action(db, "user_registered", user.id, request, {"role": body.role})

    token_data = {"sub": user.id, "role": user.role, "phone": user.phone}

    return {
        "access_token": create_access_token(token_data),
        "refresh_token": create_refresh_token(token_data),
        "token_type": "Bearer",
        "user": {
            "id": user.id,
            "full_name": user.full_name,
            "phone": user.phone,
            "role": user.role,
        },
    }


@router.post("/refresh")
async def refresh_token(body: RefreshRequest):
    """Refresh access token using a valid refresh token."""
    payload = decode_token(body.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=400, detail="Provide a refresh token, not an access token.")

    new_access = create_access_token({
        "sub": payload["sub"],
        "role": payload["role"],
        "phone": payload.get("phone"),
    })
    return {"access_token": new_access, "token_type": "Bearer"}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns the currently authenticated user's profile."""
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "email": current_user.email,
        "role": current_user.role,
        "district": current_user.district,
        "state": current_user.state,
        "is_active": current_user.is_active,
        "last_login": current_user.last_login,
    }
