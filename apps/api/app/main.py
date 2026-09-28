"""
OVERSIGHT FastAPI Application — Main Entry Point
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.tasks.scheduler import start_scheduler, stop_scheduler

# Import all routers
from app.routers import auth, attendance, analytics, institutions, inspections, realtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    print("[STARTUP] OVERSIGHT API starting up...")

    # Create all DB tables (idempotent — safe to run every time)
    await init_db()
    print("[DB] Database tables ready (Neon DB)")

    # Start background scoring scheduler
    start_scheduler(demo_mode=settings.DEMO_MODE)

    yield  # <- App runs here

    # Shutdown
    stop_scheduler()
    print("[SHUTDOWN] OVERSIGHT API shutting down.")


app = FastAPI(
    title="OVERSIGHT API",
    description=(
        "Operational Vision & Evidence-based Real-time Smart Inspection & Governance Tracking. "
        "Smart India Hackathon 2026 | Ministry of Social Justice & Empowerment"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:8081"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include Routers ───────────────────────────────────────────────────────────
app.include_router(auth.router,         prefix="/api/v1")
app.include_router(attendance.router,   prefix="/api/v1")
app.include_router(analytics.router,   prefix="/api/v1")
app.include_router(institutions.router, prefix="/api/v1")
app.include_router(inspections.router,  prefix="/api/v1")
app.include_router(realtime.router)     # WebSocket at /ws/dashboard, video at /api/v1/...


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "env": settings.APP_ENV,
        "demo_mode": settings.DEMO_MODE,
    }


@app.get("/", tags=["System"])
async def root():
    return {
        "message": "OVERSIGHT API is running.",
        "docs": "/docs",
        "health": "/health",
    }
