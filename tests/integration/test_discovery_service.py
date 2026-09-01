"""
Integration Tests for Discovery Service
"""

from datetime import date
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base
from backend.app.services.discovery.discovery_service import DiscoveryService
from backend.app.services.retrieval.retrieval_service import RetrievalService
from database.models.engineering_change import EngineeringChange, Implementation
from database.models.ideathon import IdeaSubmission, ImplementationEvidenceState
from database.models.part_bom import Assembly, BomItem, Component, Part, Subsystem
from database.models.vehicle_hierarchy import ModelGeneration, ModelYear, ProductFamily, Vehicle, VehicleModel, VehicleVariant


@pytest.fixture
async def discovery_test_session():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        # 1. Seed Product Family & Vehicle Lineage
        pf = ProductFamily(id="pf-disc-100", family_code="MOTORCYCLES_100CC", name="100cc Motorcycles")
        veh = Vehicle(id="veh-disc-spl", vehicle_code="SPLENDOR", name="Splendor", product_family_id="pf-disc-100")
        mod = VehicleModel(id="mod-disc-spl", model_code="SPLENDOR_PLUS", name="Splendor Plus", vehicle_id="veh-disc-spl")
        var = VehicleVariant(id="var-disc-spl", variant_code="SPL_DRUM", name="Splendor Plus Drum", model_id="mod-disc-spl")
        gen = ModelGeneration(id="gen-disc-spl", generation_code="SPL_G1", name="Gen 1", variant_id="var-disc-spl", start_year=2022)
        my = ModelYear(id="my-disc-spl", year_code="SPL_2024", generation_id="gen-disc-spl", calendar_year=2024)

        # 2. Seed Component Breakdown
        sub = Subsystem(id="sub-disc-eng", code="ENGINE", name="Engine")
        assy = Assembly(id="assy-disc-head", subsystem_id="sub-disc-eng", code="CYLINDER_HEAD", name="Cylinder Head Assembly")
        comp = Component(id="comp-disc-head", assembly_id="assy-disc-head", code="CYL_HEAD_COVER", name="Cylinder Head Cover Component")
        part = Part(id="part-disc-head", component_id="comp-disc-head", part_number="11100-KCC-900", part_name="Cylinder Head Cover")
        bom = BomItem(id="bom-disc-01", model_year_id="my-disc-spl", part_id="part-disc-head", quantity_per_vehicle=1.0)

        # 3. Seed Active ECN
        ecn = EngineeringChange(
            id="ecn-disc-01",
            ecn_number="ECN-2024-0010",
            title="Reduce wall thickness of 11100-KCC-900 by 0.7mm",
            description="Reduced wall thickness from 3.5mm to 2.8mm on 11100-KCC-900.",
            release_date=date(2027, 6, 1),
            change_category="COST_REDUCTION",
            status="RELEASED",
            affected_part_id="part-disc-head",
        )

        # 4. Seed Idea
        idea = IdeaSubmission(
            id="idea-disc-01",
            submission_code="IDEA-2024-0050",
            raw_title="Reduce cylinder head cover thickness on Splendor Plus",
            raw_description="High mass on 11100-KCC-900. Reduce wall thickness by 0.7mm.",
            target_vehicle_id="veh-disc-spl",
            target_model_id="SPLENDOR_PLUS",
            target_part_id="part-disc-head",
            extracted_part_number="11100-KCC-900",
            cost_reduction_category="GEOMETRY_OPTIMIZATION",
            decision_state="SUBMITTED",
            evidence_state="NOT_EVALUATED",
        )

        session.add_all([pf, veh, mod, var, gen, my, sub, assy, comp, part, bom, ecn, idea])
        await session.commit()

        # Index ECN into vector storage
        retrieval_service = RetrievalService()
        await retrieval_service.index_ecn(session, ecn)

        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_evaluate_idea_evidence_service(discovery_test_session: AsyncSession):
    session = discovery_test_session
    service = DiscoveryService()

    eval_result = await service.evaluate_idea_implementation_evidence(session, "idea-disc-01")

    assert eval_result is not None
    assert eval_result.evidence_state == ImplementationEvidenceState.IMPLEMENTATION_CONFIRMED.value
    assert len(eval_result.discovered_evidences) >= 1
    assert eval_result.confidence_score >= 0.85

    # Check that database record was updated
    stmt = select(IdeaSubmission).where(IdeaSubmission.id == "idea-disc-01")
    idea = (await session.execute(stmt)).scalars().first()
    assert idea is not None
    assert idea.evidence_state == ImplementationEvidenceState.IMPLEMENTATION_CONFIRMED.value
