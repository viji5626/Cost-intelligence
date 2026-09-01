"""
10-Tier Implementation Applicability Hierarchy Matrix Engine
Traverses:
Vehicle -> Model -> Variant -> Generation -> Model Year -> Component -> Part -> Implementation -> Engineering Change -> Project
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models.engineering_change import EngineeringChange, Implementation
from database.models.part_bom import Assembly, BomItem, Component, Part, Subsystem
from database.models.vehicle_hierarchy import ModelGeneration, ModelYear, ProductFamily, Vehicle, VehicleModel, VehicleVariant


@dataclass
class ApplicabilityNode:
    """Represents a node in the multi-tier vehicle-part-implementation applicability tree."""

    node_type: str  # VEHICLE, MODEL, VARIANT, GENERATION, MODEL_YEAR, COMPONENT, PART, IMPLEMENTATION, ECN
    node_id: str
    code: str
    name: str
    status: str = "ACTIVE"
    metadata: Dict[str, Any] = field(default_factory=dict)
    children: List["ApplicabilityNode"] = field(default_factory=list)


@dataclass
class CrossModelApplicabilitySummary:
    """Summary of cross-vehicle model sharing for a specific part/component."""

    part_id: str
    part_number: str
    part_name: str
    component_code: str
    subsystem_code: str
    total_applicable_models: int
    applicable_models: List[Dict[str, Any]]
    active_model_years: List[int]
    sibling_models_sharing_part: List[str]
    implementation_records_count: int


class ApplicabilityMatrixEngine:
    """
    Constructs multi-tier applicability trees and computes cross-model applicability
    across vehicle lines, variants, model years, and engineering change notices.
    """

    @classmethod
    async def build_part_applicability_tree(
        cls,
        session: AsyncSession,
        part_id: str,
    ) -> Optional[ApplicabilityNode]:
        """
        Builds the complete top-down applicability tree starting from the Part,
        resolving upwards through Component/Subsystem and downwards through BOM -> Model Year -> Variant -> Model -> Vehicle.
        """
        # Load part with component, assembly, subsystem, bom_items, implementations
        stmt = (
            select(Part)
            .where(Part.id == part_id)
            .options(
                selectinload(Part.component)
                .selectinload(Component.assembly)
                .selectinload(Assembly.subsystem),
                selectinload(Part.bom_items)
                .selectinload(BomItem.model_year)
                .selectinload(ModelYear.generation)
                .selectinload(ModelGeneration.variant)
                .selectinload(VehicleVariant.model)
                .selectinload(VehicleModel.vehicle),
            )
        )
        res = await session.execute(stmt)
        part = res.scalars().first()
        if not part:
            return None

        # Root Part Node
        part_node = ApplicabilityNode(
            node_type="PART",
            node_id=part.id,
            code=part.part_number,
            name=part.part_name,
            status="ACTIVE",
            metadata={
                "component_id": part.component_id,
                "weight_kg": part.weight_kg,
                "drawing_number": part.drawing_number,
            },
        )

        # Attach Component & Subsystem info
        if part.component:
            comp_node = ApplicabilityNode(
                node_type="COMPONENT",
                node_id=part.component.id,
                code=part.component.code,
                name=part.component.name,
                metadata={
                    "assembly_code": part.component.assembly.code if part.component.assembly else None,
                    "subsystem_code": (
                        part.component.assembly.subsystem.code
                        if part.component.assembly and part.component.assembly.subsystem
                        else None
                    ),
                },
            )
            part_node.children.append(comp_node)

        # Attach Model Years & Vehicle Lineage via BOM
        for bom in part.bom_items:
            if not bom.model_year:
                continue
            my = bom.model_year
            gen = my.generation
            var = gen.variant if gen else None
            mod = var.model if var else None
            veh = mod.vehicle if mod else None

            my_node = ApplicabilityNode(
                node_type="MODEL_YEAR",
                node_id=my.id,
                code=my.year_code,
                name=f"{mod.name if mod else 'Model'} ({my.calendar_year})",
                status="ACTIVE" if bom.is_active else "OBSOLETE",
                metadata={
                    "calendar_year": my.calendar_year,
                    "quantity_per_vehicle": float(bom.quantity_per_vehicle),
                    "effective_from": str(bom.effective_from) if bom.effective_from else None,
                    "effective_to": str(bom.effective_to) if bom.effective_to else None,
                    "variant_name": var.name if var else None,
                    "model_name": mod.name if mod else None,
                    "vehicle_code": veh.vehicle_code if veh else None,
                },
            )
            part_node.children.append(my_node)

        return part_node

    @classmethod
    async def get_cross_model_summary(
        cls,
        session: AsyncSession,
        part_number: str,
    ) -> Optional[CrossModelApplicabilitySummary]:
        """
        Finds all vehicle models sharing a part number and summarizes portfolio applicability.
        """
        stmt = (
            select(Part)
            .where(Part.part_number == part_number)
            .options(
                selectinload(Part.component)
                .selectinload(Component.assembly)
                .selectinload(Assembly.subsystem),
                selectinload(Part.bom_items)
                .selectinload(BomItem.model_year)
                .selectinload(ModelYear.generation)
                .selectinload(ModelGeneration.variant)
                .selectinload(VehicleVariant.model)
                .selectinload(VehicleModel.vehicle),
            )
        )
        res = await session.execute(stmt)
        part = res.scalars().first()
        if not part:
            return None

        applicable_models: Dict[str, Dict[str, Any]] = {}
        active_years: Set[int] = set()

        for bom in part.bom_items:
            if not bom.model_year or not bom.is_active:
                continue
            my = bom.model_year
            active_years.add(my.calendar_year)
            gen = my.generation
            if not gen or not gen.variant or not gen.variant.model:
                continue
            mod = gen.variant.model
            if mod.model_code not in applicable_models:
                applicable_models[mod.model_code] = {
                    "model_id": mod.id,
                    "model_code": mod.model_code,
                    "model_name": mod.name,
                    "vehicle_id": mod.vehicle_id,
                    "active_years": [my.calendar_year],
                    "variants": [gen.variant.name],
                }
            else:
                if my.calendar_year not in applicable_models[mod.model_code]["active_years"]:
                    applicable_models[mod.model_code]["active_years"].append(my.calendar_year)
                if gen.variant.name not in applicable_models[mod.model_code]["variants"]:
                    applicable_models[mod.model_code]["variants"].append(gen.variant.name)

        # Implementation records count
        impl_stmt = select(Implementation).where(Implementation.part_id == part.id)
        impl_res = await session.execute(impl_stmt)
        impl_count = len(impl_res.scalars().all())

        subsystem_code = (
            part.component.assembly.subsystem.code
            if part.component and part.component.assembly and part.component.assembly.subsystem
            else "UNKNOWN"
        )
        component_code = part.component.code if part.component else "UNKNOWN"

        models_list = list(applicable_models.values())
        sibling_models = [m["model_name"] for m in models_list]

        return CrossModelApplicabilitySummary(
            part_id=part.id,
            part_number=part.part_number,
            part_name=part.part_name,
            component_code=component_code,
            subsystem_code=subsystem_code,
            total_applicable_models=len(models_list),
            applicable_models=models_list,
            active_model_years=sorted(list(active_years)),
            sibling_models_sharing_part=sibling_models,
            implementation_records_count=impl_count,
        )
