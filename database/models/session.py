"""
User Session Model
Tracks server-side authenticated sessions with expiration and client telemetry.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.models.base import BaseModel


class UserSession(BaseModel):
    """Server-side active user session record."""

    __tablename__ = "user_sessions"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    session_token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    user = relationship("User", backref="sessions", lazy="joined")
