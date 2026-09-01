"""
Audit Log Database Model
Implements audit data minimization: stores provenance metadata, hashes, and decision IDs.
"""

from typing import Optional
from sqlalchemy import String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from database.models.base import BaseModel


class AuditLog(BaseModel):
    """Immutable audit trail recording critical decisions, source updates, and AI actions."""

    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    workflow_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    evidence_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
