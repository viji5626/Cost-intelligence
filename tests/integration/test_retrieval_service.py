"""
Integration Tests for Retrieval Service
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base
from backend.app.services.retrieval.retrieval_service import RetrievalService
from database.models.engineering_change import EngineeringChange
from database.models.ideathon import IdeaSubmission


@pytest.fixture
async def retrieval_test_session():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_index_and_hybrid_search(retrieval_test_session: AsyncSession):
    session = retrieval_test_session
    service = RetrievalService()

    # 1. Create and Index Idea
    idea = IdeaSubmission(
        id="idea-101",
        submission_code="IDEA-2024-0001",
        raw_title="Reduce cylinder head cover thickness on Splendor Plus",
        raw_description="High mass on 11100-KCC-900. Reduce wall thickness by 0.7mm.",
        extracted_part_number="11100-KCC-900",
        target_model_id="SPLENDOR_PLUS",
        cost_reduction_category="GEOMETRY_OPTIMIZATION",
        decision_state="SUBMITTED",
        evidence_state="NOT_EVALUATED",
    )
    session.add(idea)
    await session.commit()
    await service.index_idea_submission(session, idea)

    # 2. Create and Index ECN
    from datetime import date
    ecn = EngineeringChange(
        id="ecn-101",
        ecn_number="ECN-2024-0042",
        title="Rear brake pedal bushing change on Glamour",
        description="Changed bushing material on 46500-KTR-700 from bronze to polymer.",
        release_date=date(2024, 5, 10),
        change_category="COST_REDUCTION",
        status="RELEASED",
    )
    session.add(ecn)
    await session.commit()
    await service.index_ecn(session, ecn)

    # 3. Exact Part Number Search
    results_part = await service.search(session, raw_query="11100-KCC-900", top_k=5)
    assert len(results_part) >= 1
    assert results_part[0].entity_id == "idea-101"
    assert results_part[0].part_number == "11100-KCC-900"

    # 4. Semantic Search
    results_sem = await service.search(session, raw_query="Decrease aluminum thickness on engine top cover", top_k=5)
    assert len(results_sem) >= 1
    assert results_sem[0].entity_id == "idea-101"

    # 5. Exact ECN Search
    results_ecn = await service.search(session, raw_query="ECN-2024-0042", top_k=5)
    assert len(results_ecn) >= 1
    assert results_ecn[0].entity_id == "ecn-101"
