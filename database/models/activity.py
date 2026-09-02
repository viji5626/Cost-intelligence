"""
User Activity Model
Logs semantic workflow events for chronological session reconstruction.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from database.models.base import BaseModel


class UserActivityEvent(BaseModel):
    """Semantic user activity event log for workflow session reconstruction."""

    __tablename__ = "user_activity_events"

    session_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    activity_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    page: Mapped[str] = mapped_column(String(100), nullable=False)
    plant_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    details_json: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )
