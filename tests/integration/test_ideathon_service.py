"""
Integration Tests for Ideathon Service
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base
from backend.app.services.ideathon.ideathon_service import IdeathonService
from database.models.ideathon import (
    DataQualityStatus,
    IdeaDecisionState,
    IdeaDuplicateLink,
    IdeaSubmission,
    ImplementationEvidenceState,
)
from database.models.part_bom import Assembly, Component, Part, Subsystem
from database.models.vehicle_hierarchy import ProductFamily, Vehicle, VehicleModel


@pytest.fixture
async def ideathon_test_session():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        # Seed Vehicle Hierarchy & Component Breakdown
        pf = ProductFamily(id="pf-01", family_code="MOTORCYCLES_100CC", name="100cc Motorcycles")
        veh = Vehicle(id="veh-01", vehicle_code="SPLENDOR", name="Splendor", product_family_id="pf-01")
        model = VehicleModel(id="vmod-01", model_code="SPLENDOR_PLUS", name="Splendor Plus", vehicle_id="veh-01")
        
        sub = Subsystem(id="sub-01", code="ENGINE", name="Engine")
        assy = Assembly(id="assy-01", subsystem_id="sub-01", code="CYLINDER_HEAD", name="Cylinder Head Assembly")
        comp = Component(id="comp-01", assembly_id="assy-01", code="CYL_HEAD_COVER", name="Cylinder Head Cover Component")
        part = Part(id="part-01", component_id="comp-01", part_number="11100-KCC-900", part_name="Cylinder Head Cover")
        session.add_all([pf, veh, model, sub, assy, comp, part])
        await session.commit()
        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_submit_and_normalize_idea_service(ideathon_test_session: AsyncSession):
    session = ideathon_test_session

    idea = await IdeathonService.submit_and_normalize_idea(
        session=session,
        title="Reduce cylinder head cover thickness on Splendor Plus",
        description="Problem: High mass on 11100-KCC-900. Solution: Reduce wall thickness by 0.7mm. Saving: Rs 3.50 per vehicle.",
        submitter_employee_id="EMP-1045",
        submitter_plant_code="PLANT-HAR",
        raw_claimed_saving=3.50,
    )

    assert idea.id is not None
    assert idea.raw_title == "Reduce cylinder head cover thickness on Splendor Plus"
    # Immutable preservation check
    assert idea.raw_description.startswith("Problem: High mass")
    # Foreign key resolutions against master data
    assert idea.target_model_id == "vmod-01"
    assert idea.target_part_id == "part-01"
    assert idea.extracted_part_number == "11100-KCC-900"
    # Dual state verification
    assert idea.decision_state == IdeaDecisionState.SUBMITTED.value
    assert idea.evidence_state == ImplementationEvidenceState.NOT_EVALUATED.value
    assert idea.data_quality == DataQualityStatus.COMPLETE.value


@pytest.mark.asyncio
async def test_duplicate_linking_on_submission(ideathon_test_session: AsyncSession):
    session = ideathon_test_session

    # Submit Idea 1
    idea1 = await IdeathonService.submit_and_normalize_idea(
        session=session,
        title="Splendor Plus handle weight reduction",
        description="Reduce weight of handlebar weight by 50 grams.",
    )

    # Submit Idea 2 (Near duplicate of Idea 1)
    idea2 = await IdeathonService.submit_and_normalize_idea(
        session=session,
        title="Splendor Plus handle weight reduction",
        description="Reduce weight of handlebar weight by 50 grams.",
    )

    # Check duplicate link
    dup_links = (await session.execute(select(IdeaDuplicateLink))).scalars().all()
    assert len(dup_links) >= 1
    assert dup_links[0].source_idea_id == idea2.id
    assert dup_links[0].target_idea_id == idea1.id
    assert dup_links[0].similarity_score >= 0.90


@pytest.mark.asyncio
async def test_human_review_queue(ideathon_test_session: AsyncSession):
    session = ideathon_test_session

    # Submit ambiguous idea (missing vehicle)
    await IdeathonService.submit_and_normalize_idea(
        session=session,
        title="Generic bracket fastener reduction",
        description="Fastener consolidation for unspecified bracket.",
    )

    review_queue = await IdeathonService.get_human_review_queue(session)
    assert len(review_queue) >= 1
    assert review_queue[0].data_quality in [
        DataQualityStatus.AMBIGUOUS_VEHICLE.value,
        DataQualityStatus.REQUIRES_HUMAN_REVIEW.value,
    ]
