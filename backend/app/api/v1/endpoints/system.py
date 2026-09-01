"""
System and Hardware Profile Endpoints
Exposes detected host hardware, dynamic memory allocations, and execution tiers.
"""

from fastapi import APIRouter, Depends, status
from ai.hardware.models import HardwareProfile
from ai.hardware.profiler import HardwareProfiler
from backend.app.core.security import UserSession, get_current_user

router = APIRouter(prefix="/system", tags=["System & Hardware"])


@router.get(
    "/hardware-profile",
    response_model=HardwareProfile,
    status_code=status.HTTP_200_OK,
)
async def get_hardware_profile(
    current_user: UserSession = Depends(get_current_user),
) -> HardwareProfile:
    """Returns the dynamically detected host hardware resources, memory budget, and selected tier."""
    profile = HardwareProfiler.get_profile()
    return profile
