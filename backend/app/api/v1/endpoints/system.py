"""
System and Hardware Profile Endpoints
Exposes detected host hardware, dynamic memory allocations, runtime readiness, and recovery controls.
"""

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from ai.hardware.models import HardwareProfile
from ai.hardware.profiler import HardwareProfiler
from backend.app.core.database import get_db
from backend.app.core.security import UserSession, get_current_user
from backend.app.core.rbac import require_permission, HeroPermission
from backend.app.services.runtime_service import RuntimeLifecycleService

router = APIRouter(prefix="/system", tags=["System & Hardware"])


class RuntimeInitRequest(BaseModel):
    provider: str = "llama_cpp"
    model_id: str
    model_hash: str = "sha256:verified"
    runtime_profile: str = "BALANCED"
    context_length: int = 4096
    gpu_layers: int = -1


class RuntimeRecoveryRequest(BaseModel):
    reason: str


@router.get(
    "/hardware-profile",
    response_model=HardwareProfile,
    status_code=status.HTTP_200_OK,
)
async def get_hardware_profile(
    current_user: UserSession = Depends(get_current_user),
) -> HardwareProfile:
    """Returns the dynamically detected host hardware resources, memory budget, and selected tier."""
    return HardwareProfiler.get_profile()


@router.get("/readiness")
async def get_system_readiness(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Public probe returning system readiness status across security, database, and AI runtime."""
    return await RuntimeLifecycleService.get_readiness_status(db=db)


@router.post("/runtime/initialize")
async def initialize_ai_runtime(
    payload: RuntimeInitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(require_permission(HeroPermission.MANAGE_RUNTIME.value)),
) -> Dict[str, Any]:
    """Initializes and saves the default AI runtime configuration (Administrator only)."""
    return await RuntimeLifecycleService.initialize_runtime(
        db=db,
        provider=payload.provider,
        model_id=payload.model_id,
        model_hash=payload.model_hash,
        runtime_profile=payload.runtime_profile,
        context_length=payload.context_length,
        gpu_layers=payload.gpu_layers,
        configured_by=current_user.user_id,
        username=current_user.username,
    )


@router.post("/runtime/restore")
async def restore_saved_runtime(
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(require_permission(HeroPermission.MANAGE_RUNTIME.value)),
) -> Dict[str, Any]:
    """Restores the saved AI runtime profile from PostgreSQL (Administrator only)."""
    return await RuntimeLifecycleService.auto_restore_saved_runtime(db=db)


@router.post("/runtime/recovery")
async def trigger_runtime_recovery(
    payload: RuntimeRecoveryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(require_permission(HeroPermission.MANAGE_RUNTIME.value)),
) -> Dict[str, Any]:
    """Manually triggers Runtime Recovery mode for safe administrative remediation."""
    return await RuntimeLifecycleService.trigger_recovery_mode(
        db=db,
        reason=payload.reason,
        username=current_user.username,
    )
