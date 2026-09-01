"""
Integration Tests for Vehicle Hierarchy and Part Lineage Traversal Service
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base
from backend.app.services.hierarchy_service import HierarchyService
from database.models.vehicle_hierarchy import (
    ProductFamily,
    Vehicle,
    VehicleModel,
    VehicleVariant,
    ModelGeneration,
    ModelYear,
)
from database.models.part_bom import (
    Subsystem,
    Assembly,
    Component,
    Material,
    Part,
    BomItem,
)


@pytest.fixture
async def memory_db_session():
    """Provides an isolated async SQLite in-memory database session."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_full_lineage_and_applicability_traversal(memory_db_session: AsyncSession):
    session = memory_db_session

    # 1. Seed Engineering Structure
    sub = Subsystem(id="sub-01", code="SUB-CHASSIS", name="Frame and Chassis", is_safety_critical=True)
    asm = Assembly(id="asm-01", code="ASM-SWINGARM", name="Rear Swingarm Assembly", subsystem_id=sub.id, is_safety_critical=True)
    comp = Component(id="comp-01", code="COMP-BUSH", name="Swingarm Bush", assembly_id=asm.id, is_safety_critical=False)
    mat = Material(id="mat-01", material_code="MAT-ADC12", name="Alloy ADC12", material_category="METALLIC")
    part = Part(
        id="prt-01",
        part_number="52101KCC900",
        part_name="BUSH, SWINGARM PIVOT",
        component_id=comp.id,
        material_id=mat.id,
        weight_kg=0.185,
        is_safety_critical=False,
    )
    session.add_all([sub, asm, comp, mat, part])

    # 2. Seed Vehicle Hierarchy 1 (Splendor)
    fam = ProductFamily(id="fam-01", family_code="FAM-COMMUTER", name="Commuter")
    veh1 = Vehicle(id="veh-01", vehicle_code="VEH-SPL", name="Splendor", product_family_id=fam.id)
    mod1 = VehicleModel(id="mod-01", model_code="MOD-SPL-PLUS", name="Splendor+", vehicle_id=veh1.id, platform_code="PLAT-100CC")
    var1 = VehicleVariant(id="var-01", variant_code="VAR-DRUM", name="Drum Cast", model_id=mod1.id)
    gen1 = ModelGeneration(id="gen-01", generation_code="GEN-BS6", name="BS6", variant_id=var1.id, start_year=2023)
    my1 = ModelYear(id="my-01", year_code="MY2024-SPL", generation_id=gen1.id, calendar_year=2024, annual_volume_planned=450000)

    # 3. Seed Vehicle Hierarchy 2 (HF Deluxe - Sibling Model using same part!)
    veh2 = Vehicle(id="veh-02", vehicle_code="VEH-HFD", name="HF Deluxe", product_family_id=fam.id)
    mod2 = VehicleModel(id="mod-02", model_code="MOD-HFD-SELF", name="HF Deluxe Self", vehicle_id=veh2.id, platform_code="PLAT-100CC")
    var2 = VehicleVariant(id="var-02", variant_code="VAR-HFD-DRUM", name="Drum Kick", model_id=mod2.id)
    gen2 = ModelGeneration(id="gen-02", generation_code="GEN-HFD-BS6", name="BS6", variant_id=var2.id, start_year=2023)
    my2 = ModelYear(id="my-02", year_code="MY2024-HFD", generation_id=gen2.id, calendar_year=2024, annual_volume_planned=320000)

    session.add_all([fam, veh1, mod1, var1, gen1, my1, veh2, mod2, var2, gen2, my2])

    # 4. Seed BOM mappings linking part to both Model Years
    bom1 = BomItem(id="bom-01", model_year_id=my1.id, part_id=part.id, quantity_per_vehicle=2.0)
    bom2 = BomItem(id="bom-02", model_year_id=my2.id, part_id=part.id, quantity_per_vehicle=2.0)
    session.add_all([bom1, bom2])

    await session.commit()

    # 5. Test Lineage Traversal
    lineage = await HierarchyService.get_part_full_lineage(session, part.id)
    assert lineage is not None
    assert lineage["part_number"] == "52101KCC900"
    assert lineage["component"]["name"] == "Swingarm Bush"
    assert lineage["assembly"]["name"] == "Rear Swingarm Assembly"
    assert lineage["subsystem"]["name"] == "Frame and Chassis"
    assert lineage["material"]["name"] == "Alloy ADC12"
    # Upstream assembly and subsystem are safety critical -> aggregated safety critical is TRUE
    assert lineage["is_safety_critical"] is True

    # 6. Test Cross-Model Portfolio Applicability
    applicability = await HierarchyService.get_part_vehicle_applicability(session, part.id)
    assert len(applicability) == 2

    model_names = [a["model_name"] for a in applicability]
    assert "Splendor+" in model_names
    assert "HF Deluxe Self" in model_names

    total_volume = sum(a["annual_planned_volume"] for a in applicability)
    assert total_volume == (450000 + 320000)
