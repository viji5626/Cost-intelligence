"""
Integration Tests for Retrieval API Endpoints
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base, get_db
from backend.app.main import app
from datetime import date
from database.models.engineering_change import EngineeringChange
from database.models.ideathon import IdeaSubmission


@pytest.fixture
async def override_retrieval_client():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_test_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db

    async with session_maker() as session:
        idea = IdeaSubmission(
            id="idea-api-101",
            submission_code="IDEA-2024-0001",
            raw_title="Reduce cylinder head cover thickness on Splendor Plus",
            raw_description="High mass on 11100-KCC-900. Reduce wall thickness by 0.7mm.",
            extracted_part_number="11100-KCC-900",
            target_model_id="SPLENDOR_PLUS",
            cost_reduction_category="GEOMETRY_OPTIMIZATION",
            decision_state="SUBMITTED",
            evidence_state="NOT_EVALUATED",
        )
        ecn = EngineeringChange(
            id="ecn-api-101",
            ecn_number="ECN-2024-0042",
            title="Rear brake pedal bushing change on Glamour",
            description="Changed bushing material on 46500-KTR-700 from bronze to polymer.",
            release_date=date(2024, 5, 10),
            change_category="COST_REDUCTION",
            status="RELEASED",
        )
        session.add_all([idea, ecn])
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_index_all_and_search_api(override_retrieval_client: AsyncClient, auth_headers: dict):
    # 1. Trigger Index-all
    index_res = await override_retrieval_client.post("/api/v1/retrieval/index-all", headers=auth_headers)
    assert index_res.status_code == 200
    assert index_res.json()["indexed_records"] >= 2

    # 2. Search exact identifier
    search_payload = {
        "query": "11100-KCC-900",
        "top_k": 5,
        "enable_reranking": True,
    }
    search_res = await override_retrieval_client.post(
        "/api/v1/retrieval/search",
        headers=auth_headers,
        json=search_payload,
    )
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    assert results[0]["part_number"] == "11100-KCC-900"
    assert "provenance_notes" in results[0]


@pytest.mark.asyncio
async def test_retrieval_benchmark_api(override_retrieval_client: AsyncClient, auth_headers: dict):
    bm_res = await override_retrieval_client.get("/api/v1/retrieval/benchmark", headers=auth_headers)
    assert bm_res.status_code == 200
    bm_data = bm_res.json()
    assert bm_data["total_queries"] == 10
    assert bm_data["recall_at_3"] >= 0.80
    assert "p50_latency_ms" in bm_data
