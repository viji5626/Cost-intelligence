"""
Authoritative Audit Trail Service
Implements canonical SHA-256 hash chaining, data minimization, and cryptographic integrity verification.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import desc, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.audit import AuditLog


class AuditService:
    """Provides tamper-evident audit trail logging and chain verification."""

    @staticmethod
    def compute_event_hash(
        sequence_number: int,
        timestamp: datetime,
        username: str,
        action: str,
        entity_type: str,
        entity_id: Optional[str],
        status: str,
        session_id: Optional[str],
        previous_event_hash: str,
        payload_json: Optional[Dict[str, Any]],
    ) -> str:
        """Generates canonical deterministic SHA-256 event hash."""
        payload_canonical = json.dumps(payload_json or {}, sort_keys=True, separators=(",", ":"))
        ts_iso = timestamp.isoformat()
        raw_str = (
            f"{sequence_number}:{ts_iso}:{username}:{action}:{entity_type}:"
            f"{entity_id or ''}:{status}:{session_id or ''}:{previous_event_hash}:{payload_canonical}"
        )
        return "sha256:" + hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    @classmethod
    async def log_event(
        cls,
        db: AsyncSession,
        action: str,
        entity_type: str,
        entity_id: Optional[str] = None,
        user_id: Optional[str] = None,
        username: str = "SYSTEM",
        role: str = "SYSTEM",
        department: Optional[str] = None,
        scope: Optional[str] = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        client_ip: Optional[str] = None,
        payload_json: Optional[Dict[str, Any]] = None,
        status: str = "SUCCESS",
    ) -> AuditLog:
        """Records an immutable, hash-chained audit event."""
        # Find latest event in chain
        last_event_res = await db.execute(
            select(AuditLog).order_by(desc(AuditLog.sequence_number)).limit(1)
        )
        last_event = last_event_res.scalar_one_or_none()

        sequence_number = (last_event.sequence_number + 1) if (last_event and last_event.sequence_number is not None) else 1
        previous_event_hash = last_event.event_hash if last_event else ("0" * 64)
        now = datetime.now(timezone.utc)

        # Sanitize payload: strip any raw passwords or secret tokens
        clean_payload = cls._redact_secrets(payload_json or {})

        event_hash = cls.compute_event_hash(
            sequence_number=sequence_number,
            timestamp=now,
            username=username,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            status=status,
            session_id=session_id,
            previous_event_hash=previous_event_hash,
            payload_json=clean_payload,
        )

        audit_entry = AuditLog(
            id=str(uuid.uuid4()),
            sequence_number=sequence_number,
            created_at=now,
            user_id=user_id,
            username=username,
            role=role,
            department=department,
            scope=scope,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            status=status,
            session_id=session_id,
            correlation_id=correlation_id,
            client_ip=client_ip,
            payload_json=clean_payload,
            previous_event_hash=previous_event_hash,
            event_hash=event_hash,
        )
        db.add(audit_entry)
        await db.commit()
        return audit_entry

    @classmethod
    async def verify_integrity(cls, db: AsyncSession) -> Dict[str, Any]:
        """
        Traverses the full audit trail and validates cryptographic hash chain integrity.
        Detects unauthorized deletions, modifications, or reordering.
        """
        result = await db.execute(select(AuditLog).order_by(AuditLog.sequence_number.asc()))
        events = result.scalars().all()

        if not events:
            return {
                "is_valid": True,
                "total_events_checked": 0,
                "chain_status": "EMPTY",
                "message": "Audit trail is empty. Hash chain is valid by default.",
            }

        expected_prev_hash = "0" * 64

        for idx, event in enumerate(events):
            # Check previous hash link
            if event.previous_event_hash != expected_prev_hash:
                return {
                    "is_valid": False,
                    "chain_status": "TAMPERED",
                    "corrupted_at_sequence": event.sequence_number,
                    "error": (
                        f"Broken previous hash link at sequence {event.sequence_number}. "
                        f"Expected: {expected_prev_hash}, Found: {event.previous_event_hash}"
                    ),
                }

            # Check self event hash
            ts = event.created_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            recomputed_hash = cls.compute_event_hash(
                sequence_number=event.sequence_number,
                timestamp=ts,
                username=event.username,
                action=event.action,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                status=event.status,
                session_id=event.session_id,
                previous_event_hash=event.previous_event_hash,
                payload_json=event.payload_json,
            )

            if event.event_hash != recomputed_hash:
                return {
                    "is_valid": False,
                    "chain_status": "TAMPERED",
                    "corrupted_at_sequence": event.sequence_number,
                    "error": (
                        f"Event hash mismatch at sequence {event.sequence_number}. "
                        f"Expected: {recomputed_hash}, Found: {event.event_hash}"
                    ),
                }

            expected_prev_hash = event.event_hash

        return {
            "is_valid": True,
            "total_events_checked": len(events),
            "chain_status": "INTACT",
            "message": f"All {len(events)} audit trail events successfully verified with unbroken SHA-256 hash chaining.",
            "head_hash": expected_prev_hash,
        }

    @staticmethod
    def _redact_secrets(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Redacts sensitive credentials, tokens, and passwords from payloads."""
        redacted = {}
        sensitive_keys = {"password", "token", "access_token", "secret", "hashed_password", "confirm_password"}
        for k, v in payload.items():
            if any(s in k.lower() for s in sensitive_keys):
                redacted[k] = "[REDACTED]"
            elif isinstance(v, dict):
                redacted[k] = AuditService._redact_secrets(v)
            else:
                redacted[k] = v
        return redacted
