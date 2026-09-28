"""
OVERSIGHT — All SQLAlchemy ORM Models
Covers: Users, OTP, Institutions, Projects, Staff, Beneficiaries,
        Attendance, Occupancy, Invoices, Anomaly Scores, Inspections,
        Checklists, Evidence, Video Calls, Compliance History, Audit Log
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, Boolean, DateTime, Float, Integer, Text,
    ForeignKey, Enum as SAEnum, Numeric, Date, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


def now_utc():
    return datetime.now(timezone.utc)


def new_uuid():
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# USERS & AUTH
# ─────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    aadhaar_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256 only, never raw
    role: Mapped[str] = mapped_column(
        SAEnum("dosje_official", "pmu_inspector", "ngo_admin", "beneficiary", name="user_role"),
        default="beneficiary"
    )
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geo_lat: Mapped[float | None] = mapped_column(Float, nullable=True)   # Inspector home location
    geo_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    otp_requests: Mapped[list["OTPRequest"]] = relationship(back_populates="user")


class OTPRequest(Base):
    """
    Replaces Redis for OTP storage.
    Each row = one OTP send. Expired rows can be cleaned up periodically.
    """
    __tablename__ = "otp_requests"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    phone: Mapped[str] = mapped_column(String(15), index=True)
    otp_code: Mapped[str] = mapped_column(String(6))
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    user: Mapped["User | None"] = relationship(back_populates="otp_requests")


# ─────────────────────────────────────────────────────────────────────────────
# INSTITUTIONS (NGOs / Skill Centers / Welfare Homes)
# ─────────────────────────────────────────────────────────────────────────────

class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(500))
    registration_number: Mapped[str] = mapped_column(String(100), unique=True)
    institution_type: Mapped[str] = mapped_column(
        SAEnum("ngo", "skill_center", "welfare_home", "other", name="institution_type"),
        default="ngo"
    )
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Location — stored as plain lat/lng (Haversine in Python replaces PostGIS)
    geo_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_fence_radius_meters: Mapped[int] = mapped_column(Integer, default=100)

    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)

    admin_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    cctv_rtsp_endpoint: Mapped[str | None] = mapped_column(Text, nullable=True)  # encrypted in production

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    onboarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    # Relationships
    projects: Mapped[list["Project"]] = relationship(back_populates="institution")
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(back_populates="institution")
    occupancy_logs: Mapped[list["OccupancyLog"]] = relationship(back_populates="institution")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="institution")
    anomaly_scores: Mapped[list["AnomalyScore"]] = relationship(back_populates="institution")
    inspections: Mapped[list["Inspection"]] = relationship(back_populates="institution")
    compliance_history: Mapped[list["ComplianceHistory"]] = relationship(back_populates="institution")


# ─────────────────────────────────────────────────────────────────────────────
# PROJECTS / SCHEMES
# ─────────────────────────────────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"), index=True)
    scheme_name: Mapped[str] = mapped_column(String(500))
    sanctioned_amount: Mapped[float] = mapped_column(Numeric(15, 2), default=0)
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum("active", "completed", "suspended", name="project_status"),
        default="active"
    )
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    institution: Mapped["Institution"] = relationship(back_populates="projects")
    beneficiaries: Mapped[list["Beneficiary"]] = relationship(back_populates="project")


# ─────────────────────────────────────────────────────────────────────────────
# STAFF & BENEFICIARIES
# ─────────────────────────────────────────────────────────────────────────────

class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"), index=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    role_in_institution: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_project_incharge: Mapped[bool] = mapped_column(Boolean, default=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    enrollment_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum("active", "completed", "dropped", name="beneficiary_status"),
        default="active"
    )

    project: Mapped["Project | None"] = relationship(back_populates="beneficiaries")


# ─────────────────────────────────────────────────────────────────────────────
# ATTENDANCE
# ─────────────────────────────────────────────────────────────────────────────

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    recorded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))  # beneficiary/staff

    check_in_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    check_out_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Location (plain lat/lng — Haversine validates geo-fence)
    geo_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    geo_validation_status: Mapped[str] = mapped_column(
        SAEnum("valid", "outside_fence", "suspicious", name="geo_status"),
        default="valid"
    )
    distance_from_center_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    otp_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Offline sync
    sync_status: Mapped[str] = mapped_column(
        SAEnum("synced", "pending", name="sync_status"),
        default="synced"
    )

    institution: Mapped["Institution"] = relationship(back_populates="attendance_records")


# ─────────────────────────────────────────────────────────────────────────────
# CCTV OCCUPANCY LOGS (no raw video ever stored)
# ─────────────────────────────────────────────────────────────────────────────

class OccupancyLog(Base):
    __tablename__ = "occupancy_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"), index=True)
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    estimated_count: Mapped[int] = mapped_column(Integer)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)
    method: Mapped[str] = mapped_column(
        SAEnum("opencv_headcount", "manual_entry", name="occupancy_method"),
        default="manual_entry"
    )
    frame_discarded: Mapped[bool] = mapped_column(Boolean, default=True)  # privacy audit field

    institution: Mapped["Institution"] = relationship(back_populates="occupancy_logs")


# ─────────────────────────────────────────────────────────────────────────────
# INVOICES / FUND UTILIZATION
# ─────────────────────────────────────────────────────────────────────────────

class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)

    invoice_number: Mapped[str | None] = mapped_column(String(200), nullable=True)
    vendor_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    invoice_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    category: Mapped[str] = mapped_column(
        SAEnum("salary", "material", "travel", "equipment", "other", name="invoice_category"),
        default="other"
    )

    document_url: Mapped[str | None] = mapped_column(Text, nullable=True)       # Cloudinary/UploadThing URL
    submission_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)  # SHA-256 for dedup

    status: Mapped[str] = mapped_column(
        SAEnum("pending", "flagged", "approved", "rejected", name="invoice_status"),
        default="pending"
    )
    flag_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    institution: Mapped["Institution"] = relationship(back_populates="invoices")


# ─────────────────────────────────────────────────────────────────────────────
# ANOMALY SCORES (the core AI advisory output)
# ─────────────────────────────────────────────────────────────────────────────

class AnomalyScore(Base):
    __tablename__ = "anomaly_scores"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    priority_score: Mapped[float] = mapped_column(Float)   # 0.0 – 10.0
    score_version: Mapped[str] = mapped_column(String(50), default="v1_rule_based")

    # Explainable breakdown stored as JSON
    # Example: {"attendance_vs_reported": {"weight": 0.3, "raw_score": 0.8, "label": "38% gap"}, ...}
    factors: Mapped[dict] = mapped_column(JSON, default=dict)

    triggered_inspection: Mapped[bool] = mapped_column(Boolean, default=False)

    institution: Mapped["Institution"] = relationship(back_populates="anomaly_scores")


# ─────────────────────────────────────────────────────────────────────────────
# INSPECTIONS
# ─────────────────────────────────────────────────────────────────────────────

class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True)

    inspection_type: Mapped[str] = mapped_column(
        SAEnum("routine", "surprise_video", "physical", "follow_up", name="inspection_type"),
        default="physical"
    )
    status: Mapped[str] = mapped_column(
        SAEnum("scheduled", "in_progress", "submitted", "reviewed", "closed", name="inspection_status"),
        default="scheduled"
    )

    triggered_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    trigger_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    anomaly_score_id: Mapped[str | None] = mapped_column(ForeignKey("anomaly_scores.id"), nullable=True)

    assigned_inspector_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assignment_method: Mapped[str] = mapped_column(
        SAEnum("auto", "manual", name="assignment_method"),
        default="auto"
    )
    assignment_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)

    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    institution: Mapped["Institution"] = relationship(back_populates="inspections")
    checklist_items: Mapped[list["ChecklistItem"]] = relationship(back_populates="inspection")
    video_call: Mapped["VideoCallInspection | None"] = relationship(back_populates="inspection", uselist=False)


class ChecklistItem(Base):
    __tablename__ = "inspection_checklist_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id"), index=True)
    category: Mapped[str | None] = mapped_column(String(200), nullable=True)
    question: Mapped[str] = mapped_column(Text)
    response: Mapped[str | None] = mapped_column(
        SAEnum("yes", "no", "partial", "na", name="checklist_response"),
        nullable=True
    )
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_urls: Mapped[list | None] = mapped_column(JSON, nullable=True)

    geo_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    captured_offline: Mapped[bool] = mapped_column(Boolean, default=False)
    local_temp_id: Mapped[str | None] = mapped_column(String(100), nullable=True)  # client offline ID

    inspection: Mapped["Inspection"] = relationship(back_populates="checklist_items")


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO CALL INSPECTIONS
# ─────────────────────────────────────────────────────────────────────────────

class VideoCallInspection(Base):
    __tablename__ = "video_call_inspections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.id"), unique=True)
    initiated_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    participants: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{user_id, role, joined_at}]
    rtc_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        SAEnum("initiated", "active", "completed", "no_show", name="call_status"),
        default="initiated"
    )
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    no_show_recorded: Mapped[bool] = mapped_column(Boolean, default=False)

    inspection: Mapped["Inspection"] = relationship(back_populates="video_call")


# ─────────────────────────────────────────────────────────────────────────────
# COMPLIANCE HISTORY (append-only, permanent record)
# ─────────────────────────────────────────────────────────────────────────────

class ComplianceHistory(Base):
    __tablename__ = "compliance_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    institution_id: Mapped[str] = mapped_column(ForeignKey("institutions.id"), index=True)
    event_type: Mapped[str] = mapped_column(
        SAEnum(
            "inspection_completed", "score_spike", "video_call",
            "invoice_flagged", "beneficiary_complaint",
            name="compliance_event_type"
        )
    )
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String, nullable=True)
    recorded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    is_adverse: Mapped[bool] = mapped_column(Boolean, default=False)

    institution: Mapped["Institution"] = relationship(back_populates="compliance_history")


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT LOG (immutable, every sensitive action)
# ─────────────────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=new_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(200))
    target_entity: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(50), nullable=True)
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
