"""
WebSocket Manager + Video Call Router
WebSocket: live dashboard score updates (in-memory, no Redis needed for prototype)
Video Call: session initiation + token generation (Livekit-ready stub)
"""

import uuid
import os
from datetime import datetime, timezone
from typing import Dict, Set

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from livekit.api import AccessToken, VideoGrants

from app.core.database import get_db
from app.core.security import get_current_user, decode_token
from app.models.models import Inspection, VideoCallInspection, User, Institution

router = APIRouter(tags=["Realtime & Video"])

from app.core.config import settings

LIVEKIT_API_KEY    = settings.LIVEKIT_API_KEY
LIVEKIT_API_SECRET = settings.LIVEKIT_API_SECRET
LIVEKIT_URL        = settings.LIVEKIT_URL


# ── In-Memory WebSocket Connection Manager (replaces Redis for prototype) ─────

class ConnectionManager:
    def __init__(self):
        # Maps user_id → WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: str, message: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(user_id)

    async def broadcast_to_officials(self, message: dict, db: AsyncSession):
        """Send event to all connected DoSJE officials."""
        for user_id, ws in list(self.active_connections.items()):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(user_id)

    def connected_count(self) -> int:
        return len(self.active_connections)


# Global connection manager instance (shared across the app)
manager = ConnectionManager()


# ── WebSocket Endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket, token: str, db: AsyncSession = Depends(get_db)):
    """
    WebSocket endpoint for live dashboard updates.
    Connect: wss://your-api/ws/dashboard?token=<access_token>

    Events received by client:
      { "type": "SCORE_UPDATE", "institution_id": "...", "new_score": 7.2, "risk_level": "HIGH" }
      { "type": "NEW_ALERT", "institution_id": "...", "alert_type": "...", "message": "..." }
      { "type": "INSPECTION_STATUS_CHANGE", "inspection_id": "...", "new_status": "..." }
      { "type": "CALL_INITIATED", "call_id": "...", "institution_name": "..." }
    """
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await manager.connect(websocket, user_id)
    try:
        await websocket.send_json({
            "type": "CONNECTED",
            "message": "Connected to OVERSIGHT live dashboard.",
            "connected_users": manager.connected_count(),
        })

        # Keep connection alive — listen for client heartbeats
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "PONG"})

    except WebSocketDisconnect:
        manager.disconnect(user_id)


# ── Video Call Routes ──────────────────────────────────────────────────────────

class InitiateCallRequest(BaseModel):
    institution_id: str
    target_user_ids: list[str]


@router.post("/api/v1/video-calls/initiate")
async def initiate_video_call(
    body: InitiateCallRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Official initiates a surprise video call for an institution.
    Creates a surprise_video inspection + video call record.
    Returns a room token (Livekit stub — replace with real SDK in v1).
    """
    # Get institution
    inst_result = await db.execute(
        select(Institution).where(Institution.id == body.institution_id)
    )
    institution = inst_result.scalar_one_or_none()
    if not institution:
        raise HTTPException(status_code=404, detail="Institution not found.")

    # Create a surprise_video inspection
    inspection = Inspection(
        institution_id=body.institution_id,
        inspection_type="surprise_video",
        triggered_by=current_user.id,
        trigger_reason="Surprise video verification initiated by official.",
        status="in_progress",
    )
    db.add(inspection)
    await db.flush()

    # Generate room session ID
    session_id = f"oversight-{str(uuid.uuid4())[:8]}"

    # Create video call record
    call = VideoCallInspection(
        inspection_id=inspection.id,
        initiated_by=current_user.id,
        participants=[
            {"user_id": current_user.id, "role": current_user.role, "joined_at": datetime.now(timezone.utc).isoformat()}
        ],
        rtc_session_id=session_id,
        status="initiated",
    )
    db.add(call)
    await db.flush()

    # Push WebSocket alert to all connected clients
    event_payload = {
        "type": "INCOMING_CALL",
        "call_id": call.id,
        "institution_id": body.institution_id,
        "institution_name": institution.name,
        "room_name": session_id,
        "caller_name": current_user.full_name,
    }
    await manager.broadcast_to_officials(event_payload, db)

    # In production: send FCM push to target_user_ids here
    # await fcm_service.send_multicast(body.target_user_ids, title="OVERSIGHT", body="Join surprise verification call now")

    # Generate a real LiveKit Token for the Official/Inspector
    grant = VideoGrants(room_join=True, room=session_id, can_publish=True, can_subscribe=True)
    token = (
        AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(current_user.id)
        .with_name(current_user.full_name)
        .with_grants(grant)
        .to_jwt()
    )

    return {
        "call_id": call.id,
        "inspection_id": inspection.id,
        "session_id": session_id,
        "rtc_room_token": token,
        "livekit_url": LIVEKIT_URL,
        "join_url": f"/dashboard/calls/{session_id}",
        "expires_in": 300,
        "message": f"Surprise video call initiated for {institution.name}. Alert sent to NGO admin.",
    }


@router.get("/api/v1/livekit/token")
async def get_livekit_token(
    room: str = Query(..., description="The room name to join"),
    current_user: User = Depends(get_current_user),
):
    """
    Used by the NGO Admin to grab a token to join the incoming call room.
    """
    grant = VideoGrants(room_join=True, room=room, can_publish=True, can_subscribe=True)
    token = (
        AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(current_user.id)
        .with_name(current_user.full_name)
        .with_grants(grant)
        .to_jwt()
    )
    
    return {
        "token": token,
        "room": room,
        "livekit_url": LIVEKIT_URL
    }


@router.get("/video-calls/{call_id}")
async def get_call_status(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VideoCallInspection).where(VideoCallInspection.id == call_id)
    )
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Video call not found.")
    return {
        "id": call.id,
        "inspection_id": call.inspection_id,
        "status": call.status,
        "initiated_at": call.initiated_at,
        "participants": call.participants,
        "no_show_recorded": call.no_show_recorded,
    }


@router.post("/video-calls/{call_id}/no-show")
async def record_no_show(
    call_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record that the NGO did not join the surprise call (no-show)."""
    result = await db.execute(
        select(VideoCallInspection).where(VideoCallInspection.id == call_id)
    )
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found.")

    call.no_show_recorded = True
    call.status = "no_show"
    call.ended_at = datetime.now(timezone.utc)

    return {"call_id": call_id, "status": "no_show", "message": "No-show recorded. This will factor into the next anomaly score."}


# ── Helper: push a score update to all connected clients ─────────────────────

async def push_score_update(institution_id: str, new_score: float, risk_level: str, db: AsyncSession):
    """Call this from the scoring engine after computing a new score."""
    await manager.broadcast_to_officials(
        {
            "type": "SCORE_UPDATE",
            "institution_id": institution_id,
            "new_score": new_score,
            "risk_level": risk_level,
        },
        db,
    )
