"""
Unit Tests for Applicability Matrix Engine
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base
from backend.app.services.applicability.applicability_engine import ApplicabilityMatrixEngine
from database.models.part_bom import Assembly, BomItem, Component, Part, Subsystem
from database.models.vehicle_hierarchy import ModelGeneration, ModelYear, ProductFamily, Vehicle, VehicleModel, VehicleVariant


@pytest.fixture
async def hierarchy_matrix_session():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        # Seed 100cc Product Family
        pf = ProductFamily(id="pf-100", family_code="MOTORCYCLES_100CC", name="100cc Motorcycles")
        
        # Vehicle 1: Splendor
        veh1 = Vehicle(id="veh-spl", vehicle_code="SPLENDOR", name="Splendor", product_family_id="pf-100")
        mod1 = VehicleModel(id="mod-spl-plus", model_code="SPLENDOR_PLUS", name="Splendor Plus", vehicle_id="veh-spl")
        var1 = VehicleVariant(id="var-spl-drum", variant_code="SPL_DRUM", name="Splendor Plus Drum", model_id="mod-spl-plus")
        gen1 = ModelGeneration(id="gen-spl-g1", generation_code="SPL_GEN1", name="Gen 1", variant_id="var-spl-drum", start_year=2022)
        my1 = ModelYear(id="my-spl-2024", year_code="SPL_2024", generation_id="gen-spl-g1", calendar_year=2024)

        # Vehicle 2: HF Deluxe (Sibling Model sharing same horizontal 100cc cylinder head cover)
        veh2 = Vehicle(id="veh-hf", vehicle_code="HF", name="HF", product_family_id="pf-100")
        mod2 = VehicleModel(id="mod-hf-deluxe", model_code="HF_DELUXE", name="HF Deluxe", vehicle_id="veh-hf")
        var2 = VehicleVariant(id="var-hf-std", variant_code="HF_STD", name="HF Deluxe Standard", model_id="mod-hf-deluxe")
        gen2 = ModelGeneration(id="gen-hf-g1", generation_code="HF_GEN1", name="Gen 1", variant_id="var-hf-std", start_year=2022)
        my2 = ModelYear(id="my-hf-2024", year_code="HF_2024", generation_id="gen-hf-g1", calendar_year=2024)

        # Component Breakdown
        sub = Subsystem(id="sub-eng", code="ENGINE", name="Engine")
        assy = Assembly(id="assy-head", subsystem_id="sub-eng", code="CYLINDER_HEAD", name="Cylinder Head Assembly")
        comp = Component(id="comp-head-cover", assembly_id="assy-head", code="CYL_HEAD_COVER", name="Cylinder Head Cover Component")
        part = Part(id="part-head-cover", component_id="comp-head-cover", part_number="11100-KCC-900", part_name="Cylinder Head Cover")

        # BOM mappings (Shared on both Splendor Plus & HF Deluxe)
        bom1 = BomItem(id="bom-spl-01", model_year_id="my-spl-2024", part_id="part-head-cover", quantity_per_vehicle=1.0)
        bom2 = BomItem(id="bom-hf-01", model_year_id="my-hf-2024", part_id="part-head-cover", quantity_per_vehicle=1.0)

        session.add_all([pf, veh1, mod1, var1, gen1, my1, veh2, mod2, var2, gen2, my2, sub, assy, comp, part, bom1, bom2])
        await session.commit()
        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_part_applicability_tree(hierarchy_matrix_session: AsyncSession):
    session = hierarchy_matrix_session
    tree = await ApplicabilityMatrixEngine.build_part_applicability_tree(session, "part-head-cover")

    assert tree is not None
    assert tree.node_type == "PART"
    assert tree.code == "11100-KCC-900"
    # Should have Component node and 2 ModelYear nodes in children
    child_types = [c.node_type for c in tree.children]
    assert "COMPONENT" in child_types
    assert child_types.count("MODEL_YEAR") == 2


@pytest.mark.asyncio
async def test_cross_model_summary(hierarchy_matrix_session: AsyncSession):
    session = hierarchy_matrix_session
    summary = await ApplicabilityMatrixEngine.get_cross_model_summary(session, "11100-KCC-900")

    assert summary is not None
    assert summary.part_number == "11100-KCC-900"
    assert summary.total_applicable_models == 2
    assert "Splendor Plus" in summary.sibling_models_sharing_part
    assert "HF Deluxe" in summary.sibling_models_sharing_part
    assert summary.active_model_years == [2024]
