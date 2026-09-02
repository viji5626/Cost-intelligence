"""
User Activity and Session Reconstruction REST Endpoints
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.security import UserSession, get_current_user
from backend.app.core.rbac import require_permission, HeroPermission
from backend.app.services.activity_service import ActivityService

router = APIRouter(prefix="/activity", tags=["User Activity & Session Reconstruction"])


class ActivityEventRequest(BaseModel):
    activity_type: str
    page: str
    plant_id: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class TimelineEventResponse(BaseModel):
    id: str
    type: str
    timestamp: str
    activity_type: str
    page: str
    plant_id: Optional[str]
    entity_type: Optional[str]
    entity_id: Optional[str]
    status: Optional[str] = None
    sequence_number: Optional[int] = None
    event_hash: Optional[str] = None
    details: Dict[str, Any]


class SessionTimelineResponse(BaseModel):
    session_id: str
    user_id: str
    username: str
    event_count: int
    start_time: Optional[str]
    end_time: Optional[str]
    timeline: List[TimelineEventResponse]


@router.post("/events")
async def record_activity_event(
    payload: ActivityEventRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """Logs semantic user activity linked to current session."""
    session_id = current_user.session_id or "default-session"
    event = await ActivityService.log_activity(
        db=db,
        session_id=session_id,
        user_id=current_user.user_id,
        username=current_user.username,
        activity_type=payload.activity_type,
        page=payload.page,
        plant_id=payload.plant_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        details_json=payload.details,
    )
    return {"status": "recorded", "event_id": event.id}


@router.get("/sessions/{session_id}/timeline", response_model=SessionTimelineResponse)
async def get_session_timeline(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(require_permission(HeroPermission.READ_USER_ACTIVITY.value)),
) -> SessionTimelineResponse:
    """Deterministically reconstructs an end-to-end user workflow timeline (Layer 1)."""
    timeline_data = await ActivityService.reconstruct_session_timeline(db=db, session_id=session_id)
    return SessionTimelineResponse(**timeline_data)


from backend.app.services.narration_service import SessionNarrationService


@router.post("/sessions/{session_id}/narrate")
async def generate_session_narration(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(require_permission(HeroPermission.READ_USER_ACTIVITY.value)),
) -> Dict[str, Any]:
    """Generates an AI session narration from recorded workflow events with provenance."""
    return await SessionNarrationService.generate_narration(db=db, session_id=session_id)

