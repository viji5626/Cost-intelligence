"""
User Activity Monitoring and Session Reconstruction Service
Captures semantic business events and deterministically reconstructs user workflow sessions.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.activity import UserActivityEvent
from database.models.audit import AuditLog


class ActivityService:
    """Manages semantic user activity tracking and timeline reconstruction."""

    @classmethod
    async def log_activity(
        cls,
        db: AsyncSession,
        session_id: str,
        user_id: str,
        username: str,
        activity_type: str,
        page: str,
        plant_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        details_json: Optional[Dict[str, Any]] = None,
    ) -> UserActivityEvent:
        """Records a semantic activity event linked to an active session."""
        event = UserActivityEvent(
            id=str(uuid.uuid4()),
            session_id=session_id,
            user_id=user_id,
            username=username,
            activity_type=activity_type,
            page=page,
            plant_id=plant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            details_json=details_json or {},
            timestamp=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.commit()
        return event

    @classmethod
    async def reconstruct_session_timeline(
        cls,
        db: AsyncSession,
        session_id: str,
    ) -> Dict[str, Any]:
        """
        Deterministically reconstructs an end-to-end user session workflow timeline (Layer 1).
        Operates 100% independently of AI availability.
        """
        # 1. Fetch activity events
        act_res = await db.execute(
            select(UserActivityEvent)
            .where(UserActivityEvent.session_id == session_id)
            .order_by(UserActivityEvent.timestamp.asc())
        )
        activities = act_res.scalars().all()

        # 2. Fetch authoritative audit events for this session
        audit_res = await db.execute(
            select(AuditLog)
            .where(AuditLog.session_id == session_id)
            .order_by(AuditLog.created_at.asc())
        )
        audit_events = audit_res.scalars().all()

        # 3. Interleave events into a unified chronological timeline
        combined_events: List[Dict[str, Any]] = []

        for act in activities:
            ts = act.timestamp.isoformat() if act.timestamp else datetime.now(timezone.utc).isoformat()
            combined_events.append({
                "id": act.id,
                "type": "USER_ACTIVITY",
                "timestamp": ts,
                "activity_type": act.activity_type,
                "page": act.page,
                "plant_id": act.plant_id,
                "entity_type": act.entity_type,
                "entity_id": act.entity_id,
                "details": act.details_json or {},
            })

        for aud in audit_events:
            ts = aud.created_at.isoformat() if aud.created_at else datetime.now(timezone.utc).isoformat()
            combined_events.append({
                "id": aud.id,
                "type": "AUDIT_EVENT",
                "timestamp": ts,
                "activity_type": aud.action,
                "page": aud.entity_type,
                "plant_id": aud.scope,
                "entity_type": aud.entity_type,
                "entity_id": aud.entity_id,
                "status": aud.status,
                "sequence_number": aud.sequence_number,
                "event_hash": aud.event_hash,
                "details": aud.payload_json or {},
            })

        # Sort by timestamp
        combined_events.sort(key=lambda x: x["timestamp"])

        username = activities[0].username if activities else (audit_events[0].username if audit_events else "UNKNOWN")
        user_id = activities[0].user_id if activities else (audit_events[0].user_id if audit_events else "UNKNOWN")
        start_time = combined_events[0]["timestamp"] if combined_events else None
        end_time = combined_events[-1]["timestamp"] if combined_events else None

        return {
            "session_id": session_id,
            "user_id": user_id,
            "username": username,
            "event_count": len(combined_events),
            "start_time": start_time,
            "end_time": end_time,
            "timeline": combined_events,
        }
