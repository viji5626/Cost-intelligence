"""
Application Readiness Gate Module
Enforces zero false-ready policy: blocks business routes until AI runtime is initialized and health-verified.
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.security import UserSession, get_current_user
from backend.app.services.runtime_service import RuntimeLifecycleService


async def require_application_ready(
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> UserSession:
    """
    Dependency that gates normal business operations.
    If AI runtime is not initialized or in recovery mode, raises HTTP 503.
    """
    readiness = await RuntimeLifecycleService.get_readiness_status(db=db)
    if not readiness["is_ready"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "APPLICATION_NOT_READY",
                "readiness_status": readiness["status"],
                "message": readiness["message"],
                "recovery_mode": readiness["recovery_mode"],
            },
        )
    return current_user
