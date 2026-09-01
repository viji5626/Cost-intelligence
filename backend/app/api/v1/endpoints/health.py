"""
Health Check and Air-Gap Verification Endpoints
"""

from fastapi import APIRouter, status
from pydantic import BaseModel
from backend.app.core.config import settings
from backend.app.core.database import check_db_health

router = APIRouter(prefix="/health", tags=["Health & Status"])


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    air_gap_mode: bool
    database_connected: bool
    telemetry_enabled: bool


@router.get("/", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    """Liveness probe: verifies service health, air-gap mode, and database reachability."""
    db_ok = await check_db_health()
    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        air_gap_mode=settings.AIR_GAP_MODE,
        database_connected=db_ok,
        telemetry_enabled=settings.ENABLE_TELEMETRY,
    )


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> dict:
    """Readiness probe for container orchestration."""
    db_ok = await check_db_health()
    return {
        "ready": db_ok,
        "service": settings.PROJECT_NAME,
        "air_gap_verified": settings.AIR_GAP_MODE and not settings.ALLOW_EXTERNAL_EGRESS,
    }
