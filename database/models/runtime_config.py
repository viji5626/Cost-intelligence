"""
System Runtime Configuration Model
Persists the default AI provider, model, hardware profile, and health verification state.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from database.models.base import BaseModel


class SystemRuntimeConfig(BaseModel):
    """Persisted AI runtime configuration and health status."""

    __tablename__ = "system_runtime_configs"

    is_default: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="llama_cpp", nullable=False)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    model_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    runtime_profile: Mapped[str] = mapped_column(String(50), default="BALANCED", nullable=False)
    context_length: Mapped[int] = mapped_column(Integer, default=4096, nullable=False)
    gpu_layers: Mapped[int] = mapped_column(Integer, default=-1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_health_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    configured_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
