"""
Security Policy Model
Stores configurable password complexity, lockout limits, and session policies.
"""

from typing import Optional
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from database.models.base import BaseModel


class SecurityPolicy(BaseModel):
    """Configurable system security policies."""

    __tablename__ = "security_policies"

    min_password_length: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    require_uppercase: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_lowercase: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_digit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    require_special_char: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_failed_attempts: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    lockout_duration_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    session_inactivity_timeout_minutes: Mapped[int] = mapped_column(Integer, default=480, nullable=False)
    password_expiration_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
