"""
Background Scheduler — Runs anomaly scoring every 4 hours for all active institutions.
Uses APScheduler (zero-config, embedded in FastAPI — no Celery/Redis needed for prototype).
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.models import Institution, AnomalyScore
from app.services.scoring import compute_priority_score, get_risk_level

scheduler = AsyncIOScheduler()


async def run_scoring_for_all_institutions():
    """
    Scheduled job: compute priority score for every active institution.
    Runs every 4 hours in production, every 15 minutes in demo mode.
    """
    print("[SCHEDULER] Scoring job started...")
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                select(Institution).where(Institution.is_active == True)
            )
            institutions = result.scalars().all()

            for institution in institutions:
                try:
                    score = await compute_priority_score(db, institution.id)
                    risk = get_risk_level(score.priority_score)
                    print(f"  [OK] {institution.name}: {score.priority_score:.1f} ({risk})")

                    # Push WebSocket update if score is significant
                    # (import here to avoid circular imports)
                    from app.routers.realtime import push_score_update
                    await push_score_update(institution.id, score.priority_score, risk, db)

                except Exception as e:
                    print(f"  [ERR] Error scoring {institution.name}: {e}")

            await db.commit()
            print(f"[SCHEDULER] Scoring complete for {len(institutions)} institutions.")

        except Exception as e:
            await db.rollback()
            print(f"[SCHEDULER] Scoring job failed: {e}")


def start_scheduler(demo_mode: bool = True):
    """Start the background scoring scheduler."""
    interval_minutes = 15 if demo_mode else 240

    scheduler.add_job(
        run_scoring_for_all_institutions,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="scoring_job",
        name="Institution Anomaly Scoring",
        replace_existing=True,
    )
    scheduler.start()
    print(f"[SCHEDULER] Scoring scheduler started (every {interval_minutes} min)")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("[SCHEDULER] Scoring scheduler stopped.")
