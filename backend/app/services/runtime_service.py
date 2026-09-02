"""
AI Runtime Lifecycle and Readiness Service
Manages mandatory AI initialization, automatic startup restore, and safe Recovery Mode.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from database.models.auth import User
from database.models.runtime_config import SystemRuntimeConfig
from backend.app.services.audit_service import AuditService


class RuntimeLifecycleService:
    """Manages AI runtime readiness state, boot restoration, and failure recovery."""

    # In-memory runtime state cache
    _is_model_loaded: bool = False
    _is_healthy: bool = False
    _active_model_id: Optional[str] = None
    _active_provider: Optional[str] = None
    _active_runtime_profile: Optional[str] = None
    _recovery_mode: bool = False
    _recovery_reason: Optional[str] = None

    @classmethod
    def get_in_memory_state(cls) -> Dict[str, Any]:
        return {
            "is_model_loaded": cls._is_model_loaded,
            "is_healthy": cls._is_healthy,
            "active_model_id": cls._active_model_id,
            "active_provider": cls._active_provider,
            "active_runtime_profile": cls._active_runtime_profile,
            "recovery_mode": cls._recovery_mode,
            "recovery_reason": cls._recovery_reason,
        }

    @classmethod
    def set_mock_ready_for_test(cls, model_id: str = "qwen2.5-coder-7b-instruct-q4_k_m.gguf"):
        """Helper for unit tests to simulate active runtime."""
        cls._is_model_loaded = True
        cls._is_healthy = True
        cls._active_model_id = model_id
        cls._active_provider = "llama_cpp"
        cls._active_runtime_profile = "BALANCED"
        cls._recovery_mode = False
        cls._recovery_reason = None

    @classmethod
    def set_recovery_for_test(cls, reason: str = "Model file corrupted"):
        """Helper for unit tests to simulate recovery state."""
        cls._is_model_loaded = False
        cls._is_healthy = False
        cls._recovery_mode = True
        cls._recovery_reason = reason

    @classmethod
    async def get_readiness_status(cls, db: AsyncSession) -> Dict[str, Any]:
        """Evaluates overall platform readiness across security, persistence, and AI runtime."""
        # 1. Check if first-boot admin exists
        admin_res = await db.execute(
            select(User).where(User.role == "ADMINISTRATOR", User.is_active.is_(True)).limit(1)
        )
        has_admin = admin_res.scalar_one_or_none() is not None

        # 2. Check if default runtime config exists in DB
        cfg_res = await db.execute(
            select(SystemRuntimeConfig).where(SystemRuntimeConfig.is_default.is_(True), SystemRuntimeConfig.is_active.is_(True)).limit(1)
        )
        saved_config = cfg_res.scalar_one_or_none()

        # Determine state
        if not has_admin:
            status_code = "NEEDS_BOOTSTRAP"
            is_ready = False
            message = "First-boot administrator setup required."
        elif cls._recovery_mode:
            status_code = "RECOVERY_REQUIRED"
            is_ready = False
            message = f"AI Runtime entered Recovery Mode: {cls._recovery_reason or 'Health check failed'}"
        elif not saved_config and not cls._is_model_loaded:
            status_code = "NEEDS_RUNTIME_INIT"
            is_ready = False
            message = "Mandatory AI runtime initialization required before business access."
        elif cls._is_model_loaded and cls._is_healthy:
            status_code = "READY"
            is_ready = True
            message = "System operational. Security, audit, and AI runtime ready."
        elif saved_config:
            # Saved config exists but not yet loaded into memory
            status_code = "READY_TO_RESTORE"
            is_ready = False
            message = "Saved runtime configuration discovered. Ready to restore."
        else:
            status_code = "UNINITIALIZED"
            is_ready = False
            message = "AI Runtime uninitialized."

        return {
            "status": status_code,
            "is_ready": is_ready,
            "is_admin_configured": has_admin,
            "has_saved_config": saved_config is not None,
            "saved_model_id": saved_config.model_id if saved_config else None,
            "saved_provider": saved_config.provider if saved_config else None,
            "active_model_id": cls._active_model_id,
            "active_provider": cls._active_provider,
            "recovery_mode": cls._recovery_mode,
            "recovery_reason": cls._recovery_reason,
            "message": message,
        }

    @classmethod
    async def initialize_runtime(
        cls,
        db: AsyncSession,
        provider: str,
        model_id: str,
        model_hash: str,
        runtime_profile: str,
        context_length: int = 4096,
        gpu_layers: int = -1,
        configured_by: Optional[str] = None,
        username: str = "ADMIN",
    ) -> Dict[str, Any]:
        """Initializes and persists the default AI runtime."""
        # Unset previous defaults
        await db.execute(
            update(SystemRuntimeConfig).values(is_default=False)
        )

        now = datetime.now(timezone.utc)
        config_entry = SystemRuntimeConfig(
            id=str(uuid.uuid4()),
            is_default=True,
            provider=provider,
            model_id=model_id,
            model_hash=model_hash,
            runtime_profile=runtime_profile,
            context_length=context_length,
            gpu_layers=gpu_layers,
            is_active=True,
            last_health_verified_at=now,
            configured_by=configured_by,
        )
        db.add(config_entry)

        # Update in-memory state
        cls._is_model_loaded = True
        cls._is_healthy = True
        cls._active_model_id = model_id
        cls._active_provider = provider
        cls._active_runtime_profile = runtime_profile
        cls._recovery_mode = False
        cls._recovery_reason = None

        # Record audit event
        await AuditService.log_event(
            db=db,
            action="SYSTEM_RUNTIME_INITIALIZED",
            entity_type="AI_RUNTIME",
            entity_id=model_id,
            user_id=configured_by,
            username=username,
            role="ADMINISTRATOR",
            payload_json={
                "provider": provider,
                "model_id": model_id,
                "runtime_profile": runtime_profile,
                "context_length": context_length,
                "gpu_layers": gpu_layers,
            },
        )
        await db.commit()

        return {
            "status": "READY",
            "message": f"AI Runtime initialized with model '{model_id}' ({provider}).",
            "runtime_config_id": config_entry.id,
            "last_health_verified_at": now.isoformat(),
        }

    @classmethod
    async def auto_restore_saved_runtime(cls, db: AsyncSession) -> Dict[str, Any]:
        """Restores saved AI runtime from database configuration."""
        cfg_res = await db.execute(
            select(SystemRuntimeConfig)
            .where(SystemRuntimeConfig.is_default.is_(True), SystemRuntimeConfig.is_active.is_(True))
            .limit(1)
        )
        config = cfg_res.scalar_one_or_none()

        if not config:
            return {
                "status": "NO_SAVED_CONFIG",
                "is_restored": False,
                "message": "No default runtime configuration found in database.",
            }

        # In production this loads via AI-05 swapper.
        cls._is_model_loaded = True
        cls._is_healthy = True
        cls._active_model_id = config.model_id
        cls._active_provider = config.provider
        cls._active_runtime_profile = config.runtime_profile
        cls._recovery_mode = False
        cls._recovery_reason = None

        config.last_health_verified_at = datetime.now(timezone.utc)
        await db.commit()

        return {
            "status": "RESTORED_READY",
            "is_restored": True,
            "model_id": config.model_id,
            "provider": config.provider,
            "message": f"Successfully auto-restored saved model '{config.model_id}'.",
        }

    @classmethod
    async def trigger_recovery_mode(
        cls,
        db: AsyncSession,
        reason: str,
        username: str = "SYSTEM",
    ) -> Dict[str, Any]:
        """Puts the system into Runtime Recovery mode, protecting business operations."""
        cls._is_model_loaded = False
        cls._is_healthy = False
        cls._recovery_mode = True
        cls._recovery_reason = reason

        await AuditService.log_event(
            db=db,
            action="RUNTIME_RECOVERY_TRIGGERED",
            entity_type="AI_RUNTIME",
            entity_id=cls._active_model_id or "UNKNOWN",
            username=username,
            role="SYSTEM",
            status="WARNING",
            payload_json={"reason": reason},
        )
        return {
            "status": "RECOVERY_MODE_ACTIVE",
            "recovery_reason": reason,
            "message": "System entered Runtime Recovery mode. Normal business operations gated.",
        }
