"""
Vehicle & Part Hierarchy Traversal Service
Provides recursive relational traversals and cross-model applicability queries.
"""

from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models.vehicle_hierarchy import (
    ModelGeneration,
    ModelYear,
    Vehicle,
    VehicleModel,
    VehicleVariant,
    ProductFamily,
)
from database.models.part_bom import (
    Assembly,
    BomItem,
    Component,
    Part,
    Subsystem,
)


class HierarchyService:
    """Relational hierarchy query and lineage service."""

    @staticmethod
    async def get_part_full_lineage(session: AsyncSession, part_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves full engineering lineage: Part -> Component -> Assembly -> Subsystem -> Material."""
        stmt = (
            select(Part)
            .where(Part.id == part_id)
            .options(
                selectinload(Part.component)
                .selectinload(Component.assembly)
                .selectinload(Assembly.subsystem),
                selectinload(Part.material),
            )
        )
        result = await session.execute(stmt)
        part = result.scalar_one_or_none()
        if not part:
            return None

        component = part.component
        assembly = component.assembly if component else None
        subsystem = assembly.subsystem if assembly else None

        is_safety_critical = bool(
            part.is_safety_critical
            or (component and component.is_safety_critical)
            or (assembly and assembly.is_safety_critical)
            or (subsystem and subsystem.is_safety_critical)
        )

        return {
            "part_id": part.id,
            "part_number": part.part_number,
            "part_name": part.part_name,
            "drawing_number": part.drawing_number,
            "weight_kg": part.weight_kg,
            "is_safety_critical": is_safety_critical,
            "component": {
                "id": component.id,
                "code": component.code,
                "name": component.name,
            } if component else None,
            "assembly": {
                "id": assembly.id,
                "code": assembly.code,
                "name": assembly.name,
            } if assembly else None,
            "subsystem": {
                "id": subsystem.id,
                "code": subsystem.code,
                "name": subsystem.name,
            } if subsystem else None,
            "material": {
                "id": part.material.id,
                "code": part.material.material_code,
                "name": part.material.name,
                "category": part.material.material_category,
            } if part.material else None,
        }

    @staticmethod
    async def get_part_vehicle_applicability(session: AsyncSession, part_id: str) -> List[Dict[str, Any]]:
        """Finds all Vehicle Models, Variants, and Model Years across the portfolio using this part."""
        stmt = (
            select(BomItem)
            .where(BomItem.part_id == part_id, BomItem.is_active.is_(True))
            .options(
                selectinload(BomItem.model_year)
                .selectinload(ModelYear.generation)
                .selectinload(ModelGeneration.variant)
                .selectinload(VehicleVariant.model)
                .selectinload(VehicleModel.vehicle)
                .selectinload(Vehicle.product_family)
            )
        )
        result = await session.execute(stmt)
        bom_items = result.scalars().all()

        applicability = []
        for item in bom_items:
            my = item.model_year
            gen = my.generation if my else None
            variant = gen.variant if gen else None
            model = variant.model if variant else None
            vehicle = model.vehicle if model else None
            family = vehicle.product_family if vehicle else None

            applicability.append({
                "bom_item_id": item.id,
                "quantity_per_vehicle": float(item.quantity_per_vehicle),
                "model_year_id": my.id if my else None,
                "model_year_code": my.year_code if my else None,
                "calendar_year": my.calendar_year if my else None,
                "annual_planned_volume": my.annual_volume_planned if my else 0,
                "variant_id": variant.id if variant else None,
                "variant_name": variant.name if variant else None,
                "model_id": model.id if model else None,
                "model_name": model.name if model else None,
                "platform_code": model.platform_code if model else None,
                "vehicle_name": vehicle.name if vehicle else None,
                "product_family_name": family.name if family else None,
            })

        return applicability
