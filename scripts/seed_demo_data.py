"""
Demo Seed Script — Populates Neon DB with realistic demo data for judges.

Creates:
  - 4 users (1 official, 1 inspector, 1 NGO admin, 1 beneficiary)
  - 3 institutions (1 HIGH risk, 1 MEDIUM risk, 1 LOW risk)
  - Attendance records, CCTV occupancy logs, invoices, anomaly scores

Run: python scripts/seed_demo_data.py
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import random

# Resolve paths relative to THIS script — works from any cwd
SCRIPT_DIR = Path(__file__).resolve().parent          # scripts/
REPO_ROOT  = SCRIPT_DIR.parent                        # OVERSIGHT/
API_DIR    = REPO_ROOT / "apps" / "api"               # apps/api/

# Add api/ to Python path so `from app.xxx import ...` works
sys.path.insert(0, str(API_DIR))

from dotenv import load_dotenv
load_dotenv(API_DIR / ".env")

from app.core.database import AsyncSessionLocal, init_db
from app.models.models import (
    User, Institution, Project, Beneficiary, Staff,
    AttendanceRecord, OccupancyLog, Invoice, AnomalyScore, ComplianceHistory
)


def now():
    return datetime.now(timezone.utc)


def days_ago(n):
    return now() - timedelta(days=n)


async def seed():
    await init_db()

    async with AsyncSessionLocal() as db:
        print("🌱 Seeding demo data...")

        # ── USERS ─────────────────────────────────────────────────────────────

        official = User(
            full_name="Rajesh Kumar (DoSJE Official)",
            phone="9000000001",
            role="dosje_official",
            state="Maharashtra",
            district="Mumbai",
            is_active=True,
        )
        inspector = User(
            full_name="Priya Sharma (PMU Inspector)",
            phone="9000000002",
            role="pmu_inspector",
            state="Maharashtra",
            district="Pune",
            geo_lat=18.5204,
            geo_lng=73.8567,
            is_active=True,
        )
        ngo_admin = User(
            full_name="Suresh Patel (NGO Admin)",
            phone="9000000003",
            role="ngo_admin",
            state="Maharashtra",
            district="Nagpur",
            is_active=True,
        )
        beneficiary_user = User(
            full_name="Meera Devi (Beneficiary)",
            phone="9000000004",
            role="beneficiary",
            state="Maharashtra",
            district="Nagpur",
            is_active=True,
        )
        db.add_all([official, inspector, ngo_admin, beneficiary_user])
        await db.flush()
        print("  ✅ Users created")

        # ── INSTITUTIONS ──────────────────────────────────────────────────────

        # HIGH RISK — inflated attendance, CCTV mismatch, flagged invoices
        inst_high = Institution(
            name="Asha Skill Development Center",
            registration_number="NGO-MH-2019-001",
            institution_type="skill_center",
            address="Ward 5, Nagpur, Maharashtra",
            geo_lat=21.1458,
            geo_lng=79.0882,
            geo_fence_radius_meters=100,
            district="Nagpur",
            state="Maharashtra",
            admin_user_id=ngo_admin.id,
        )

        # MEDIUM RISK — some attendance gaps
        inst_medium = Institution(
            name="Savitribai Phule Women's Welfare Home",
            registration_number="NGO-MH-2020-042",
            institution_type="welfare_home",
            address="Hadapsar, Pune, Maharashtra",
            geo_lat=18.5089,
            geo_lng=73.9259,
            geo_fence_radius_meters=150,
            district="Pune",
            state="Maharashtra",
            admin_user_id=ngo_admin.id,
        )

        # LOW RISK — compliant
        inst_low = Institution(
            name="Ambedkar Education Trust",
            registration_number="NGO-MH-2018-007",
            institution_type="ngo",
            address="Bandra, Mumbai, Maharashtra",
            geo_lat=19.0596,
            geo_lng=72.8295,
            geo_fence_radius_meters=100,
            district="Mumbai",
            state="Maharashtra",
            admin_user_id=ngo_admin.id,
        )

        db.add_all([inst_high, inst_medium, inst_low])
        await db.flush()
        print("  ✅ Institutions created")

        # ── PROJECTS ──────────────────────────────────────────────────────────

        proj_high = Project(
            institution_id=inst_high.id,
            scheme_name="PMKVY Skill Training — Batch 2026",
            sanctioned_amount=1500000,
            start_date=datetime(2026, 4, 1).date(),
            end_date=datetime(2027, 3, 31).date(),
            status="active",
            created_by=official.id,
        )
        proj_low = Project(
            institution_id=inst_low.id,
            scheme_name="Post-Matric Scholarship Support",
            sanctioned_amount=800000,
            start_date=datetime(2026, 4, 1).date(),
            end_date=datetime(2027, 3, 31).date(),
            status="active",
            created_by=official.id,
        )
        db.add_all([proj_high, proj_low])
        await db.flush()

        # ── BENEFICIARIES (15 enrolled in HIGH RISK institution) ──────────────

        beneficiaries = []
        for i in range(15):
            ben_user = User(
                full_name=f"Beneficiary Demo {i+1:02d}",
                phone=f"800000{i+1:04d}",
                role="beneficiary",
                state="Maharashtra",
                district="Nagpur",
            )
            db.add(ben_user)
            await db.flush()
            ben = Beneficiary(
                user_id=ben_user.id,
                institution_id=inst_high.id,
                project_id=proj_high.id,
                enrollment_date=datetime(2026, 4, 1).date(),
                status="active",
            )
            beneficiaries.append(ben)
        db.add_all(beneficiaries)
        await db.flush()
        print("  ✅ 15 beneficiaries enrolled in HIGH-RISK institution")

        # ── ATTENDANCE RECORDS (HIGH RISK — only ~8/15 check-in, expect 12+) ──

        for day_offset in range(14):
            date = now() - timedelta(days=day_offset)
            # Only 7-9 check-ins per day (institution claims 15 enrolled, ~80% = 12 expected)
            checkin_count = random.randint(6, 9)  # deliberately low
            for i in range(checkin_count):
                rec = AttendanceRecord(
                    institution_id=inst_high.id,
                    project_id=proj_high.id,
                    recorded_by=beneficiaries[i % len(beneficiaries)].user_id,
                    check_in_time=date.replace(hour=9, minute=random.randint(0, 30)),
                    geo_lat=21.1458 + random.uniform(-0.0005, 0.0005),
                    geo_lng=79.0882 + random.uniform(-0.0005, 0.0005),
                    geo_validation_status="valid",
                    distance_from_center_m=random.uniform(10, 80),
                    otp_verified=True,
                )
                db.add(rec)

        # LOW RISK — healthy 13-14 check-ins per day
        for day_offset in range(14):
            date = now() - timedelta(days=day_offset)
            for i in range(random.randint(12, 14)):
                rec = AttendanceRecord(
                    institution_id=inst_low.id,
                    project_id=proj_low.id,
                    recorded_by=official.id,  # placeholder
                    check_in_time=date.replace(hour=9, minute=random.randint(0, 45)),
                    geo_lat=19.0596 + random.uniform(-0.0005, 0.0005),
                    geo_lng=72.8295 + random.uniform(-0.0005, 0.0005),
                    geo_validation_status="valid",
                    otp_verified=True,
                )
                db.add(rec)

        await db.flush()
        print("  ✅ Attendance records seeded")

        # ── CCTV OCCUPANCY LOGS (HIGH RISK — only 4-6 people visible on CCTV) ─

        for day_offset in range(7):
            for hour in [10, 12, 14]:
                sample_time = now() - timedelta(days=day_offset, hours=(now().hour - hour))
                # CCTV shows 4–6 people, but app shows 7–9 check-ins — big mismatch
                cctv_count = random.randint(4, 6)
                log = OccupancyLog(
                    institution_id=inst_high.id,
                    sampled_at=sample_time,
                    estimated_count=cctv_count,
                    confidence_score=0.82,
                    method="opencv_headcount",
                    frame_discarded=True,
                )
                db.add(log)

        await db.flush()
        print("  ✅ CCTV occupancy logs seeded")

        # ── INVOICES (HIGH RISK — 2 flagged) ─────────────────────────────────

        inv1 = Invoice(
            institution_id=inst_high.id,
            project_id=proj_high.id,
            invoice_number="INV-2026-0091",
            vendor_name="Tech Solutions Pvt Ltd",
            amount=245000,
            invoice_date=datetime(2026, 8, 15).date(),
            category="equipment",
            submission_hash="abc123hash",
            status="pending",
            uploaded_by=ngo_admin.id,
        )
        # Duplicate hash invoice → flagged
        inv2 = Invoice(
            institution_id=inst_high.id,
            project_id=proj_high.id,
            invoice_number="INV-2026-0091",  # Same number!
            vendor_name="Tech Solutions Pvt Ltd",
            amount=245000,
            invoice_date=datetime(2026, 9, 1).date(),
            category="equipment",
            submission_hash="abc123hash",  # Same hash = duplicate document!
            status="flagged",
            flag_reason="Duplicate invoice: same document hash as INV-2026-0091 submitted on 2026-08-15",
            uploaded_by=ngo_admin.id,
        )
        # Amount spike invoice
        inv3 = Invoice(
            institution_id=inst_high.id,
            project_id=proj_high.id,
            invoice_number="INV-2026-0105",
            vendor_name="Office Supplies Co",
            amount=380000,  # 3x the usual material invoices
            invoice_date=datetime(2026, 9, 10).date(),
            category="material",
            status="flagged",
            flag_reason="Amount spike: ₹3,80,000 is 3.2x above average material spend for this institution",
            uploaded_by=ngo_admin.id,
        )
        db.add_all([inv1, inv2, inv3])
        await db.flush()
        print("  ✅ Invoices seeded (2 flagged)")

        # ── ANOMALY SCORES — Historical (4 weeks of scores for HIGH RISK) ────

        scores_data = [
            (28, 2.1),  # 4 weeks ago — low
            (21, 4.5),  # 3 weeks ago — medium
            (14, 6.8),  # 2 weeks ago — HIGH
            (7,  7.2),  # 1 week ago — HIGH
            (1,  8.5),  # today — CRITICAL
        ]

        for days, score in scores_data:
            factors = {
                "attendance_vs_reported": {
                    "weight": 0.30,
                    "raw_score": min(1.0, score / 10 * 1.1),
                    "label": f"App check-ins ({random.randint(6,9)}) are ~40% below expected (12) over last 7 days."
                },
                "cctv_vs_checkins": {
                    "weight": 0.30,
                    "raw_score": min(1.0, score / 10 * 1.05),
                    "label": "CCTV avg occupancy (5.1) is 43% below app check-ins (9.0/day)."
                },
                "invoice_anomaly": {
                    "weight": 0.20,
                    "raw_score": 0.7 if score > 5 else 0.0,
                    "label": "2 invoices flagged for anomalies." if score > 5 else "No invoice anomalies."
                },
                "historical_pattern": {
                    "weight": 0.10,
                    "raw_score": 0.6 if score > 6 else 0.3,
                    "label": "High risk scores in 2 of the last 4 weeks."
                },
                "call_compliance": {
                    "weight": 0.10,
                    "raw_score": 1.0 if score > 7 else 0.0,
                    "label": "1 of 1 surprise calls was a no-show." if score > 7 else "No calls conducted yet."
                },
            }
            anomaly = AnomalyScore(
                institution_id=inst_high.id,
                project_id=proj_high.id,
                computed_at=now() - timedelta(days=days),
                priority_score=score,
                factors=factors,
            )
            db.add(anomaly)

        # LOW RISK — consistently low scores
        for days in [28, 21, 14, 7, 1]:
            db.add(AnomalyScore(
                institution_id=inst_low.id,
                computed_at=now() - timedelta(days=days),
                priority_score=round(random.uniform(0.8, 2.2), 1),
                factors={"attendance_vs_reported": {"weight": 0.30, "raw_score": 0.1, "label": "Attendance consistent with expected."}},
            ))

        await db.flush()
        print("  ✅ Anomaly scores seeded")

        # ── COMPLIANCE HISTORY ───────────────────────────────────────────────

        db.add(ComplianceHistory(
            institution_id=inst_high.id,
            event_type="score_spike",
            summary="Priority score reached 8.5 (CRITICAL). Duplicate invoice and CCTV mismatch detected.",
            is_adverse=True,
            recorded_by=official.id,
        ))
        db.add(ComplianceHistory(
            institution_id=inst_high.id,
            event_type="invoice_flagged",
            summary="Invoice INV-2026-0091 flagged: duplicate document hash detected.",
            is_adverse=True,
            recorded_by=official.id,
        ))

        await db.commit()

        print("\n" + "="*60)
        print("✅ DEMO DATA SEEDED SUCCESSFULLY!")
        print("="*60)
        print("\n📋 Demo Accounts:")
        print(f"  Official:    phone=9000000001  (DoSJE Official)")
        print(f"  Inspector:   phone=9000000002  (PMU Inspector, Pune)")
        print(f"  NGO Admin:   phone=9000000003  (NGO Admin)")
        print(f"  Beneficiary: phone=9000000004")
        print("\n⚠️  Use any OTP shown in the /api/v1/auth/send-otp response (DEMO_MODE=True)")
        print("\n🏢 Demo Institutions:")
        print(f"  HIGH RISK:   Asha Skill Development Center (score: 8.5)")
        print(f"  MEDIUM RISK: Savitribai Phule Women's Welfare Home")
        print(f"  LOW RISK:    Ambedkar Education Trust (score: ~1.5)")
        print(f"\n🌐 API Docs: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(seed())
