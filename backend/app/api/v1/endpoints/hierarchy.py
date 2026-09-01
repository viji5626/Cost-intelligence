"""
Master Data and Vehicle Hierarchy API Endpoints
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.security import UserSession, get_current_user
from backend.app.services.hierarchy_service import HierarchyService
from database.models.vehicle_hierarchy import ProductFamily, Vehicle, VehicleModel, ModelYear
from database.models.part_bom import Part, Subsystem
from database.models.plant_opex import Plant

router = APIRouter(prefix="/hierarchy", tags=["Vehicle & Master Data Hierarchy"])


@router.get("/summary", response_model=Dict[str, int])
async def get_master_data_summary(
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> Dict[str, int]:
    """Returns total count of registered master entities."""
    plants_count = (await db.execute(select(Plant))).scalars().all()
    families_count = (await db.execute(select(ProductFamily))).scalars().all()
    vehicles_count = (await db.execute(select(Vehicle))).scalars().all()
    models_count = (await db.execute(select(VehicleModel))).scalars().all()
    parts_count = (await db.execute(select(Part))).scalars().all()
    subsystems_count = (await db.execute(select(Subsystem))).scalars().all()

    return {
        "plants": len(plants_count),
        "product_families": len(families_count),
        "vehicles": len(vehicles_count),
        "vehicle_models": len(models_count),
        "parts": len(parts_count),
        "subsystems": len(subsystems_count),
    }


@router.get("/parts/{part_id}/lineage", response_model=Dict[str, Any])
async def get_part_lineage(
    part_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> Dict[str, Any]:
    """Retrieves full engineering breakdown lineage for a specific part."""
    lineage = await HierarchyService.get_part_full_lineage(db, part_id)
    if not lineage:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")
    return lineage


@router.get("/parts/{part_id}/applicability", response_model=List[Dict[str, Any]])
async def get_part_applicability(
    part_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    """Retrieves all vehicle models and model years using this part across Hero portfolio."""
    applicability = await HierarchyService.get_part_vehicle_applicability(db, part_id)
    return applicability
