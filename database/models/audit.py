"""
Audit Log Database Model
Implements authoritative tamper-evident audit trail with SHA-256 hash chaining.
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from database.models.base import BaseModel


class AuditLog(BaseModel):
    """Authoritative audit trail recording critical decisions, source updates, and security events."""

    __tablename__ = "audit_logs"

    sequence_number: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, index=True, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    username: Mapped[str] = mapped_column(String(100), default="SYSTEM", index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="SYSTEM", nullable=False)
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    scope: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="SUCCESS", nullable=False)
    workflow_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    decision: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    evidence_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    payload_json: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    previous_event_hash: Mapped[str] = mapped_column(String(64), default="0" * 64, nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), default="0" * 64, index=True, nullable=False)
