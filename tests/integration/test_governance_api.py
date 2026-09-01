"""
Integration Tests for Governance REST API Endpoints
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base, get_db
from backend.app.main import app
from database.models.auth import User
from database.models.ideathon import IdeaDecisionState, IdeaOpportunityEvaluation, IdeaSubmission, ImplementationEvidenceState
from database.models.part_bom import Assembly, BomItem, Component, ComponentCost, Part, Subsystem
from database.models.vehicle_hierarchy import ModelGeneration, ModelYear, ProductFamily, Vehicle, VehicleModel, VehicleVariant


@pytest.fixture
async def override_governance_client():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_test_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db

    async with session_maker() as session:
        pf = ProductFamily(id="pf-gapi-100", family_code="MOTORCYCLES_100CC", name="100cc Motorcycles")
        veh = Vehicle(id="veh-gapi-spl", vehicle_code="SPLENDOR", name="Splendor", product_family_id="pf-gapi-100")
        mod = VehicleModel(id="mod-gapi-spl", model_code="SPLENDOR_PLUS", name="Splendor Plus", vehicle_id="veh-gapi-spl")
        var = VehicleVariant(id="var-gapi-spl", variant_code="SPL_DRUM", name="Splendor Plus Drum", model_id="mod-gapi-spl")
        gen = ModelGeneration(id="gen-gapi-spl", generation_code="SPL_G1", name="Gen 1", variant_id="var-gapi-spl", start_year=2022)
        my = ModelYear(id="my-gapi-spl", year_code="SPL_2024", generation_id="gen-gapi-spl", calendar_year=2024, annual_volume_planned=1000000)

        sub = Subsystem(id="sub-gapi-brk", code="BRAKE_SYSTEM", name="Brake System")
        assy = Assembly(id="assy-gapi-brk", subsystem_id="sub-gapi-brk", code="DRUM_BRAKE", name="Drum Brake Assembly")
        comp = Component(id="comp-gapi-brk", assembly_id="assy-gapi-brk", code="BRAKE_LEVER", name="Brake Lever Component")
        part = Part(
            id="part-gapi-brk",
            component_id="comp-gapi-brk",
            part_number="53100-KTR-900",
            part_name="Front Brake Lever",
            is_safety_critical=True,
        )

        idea = IdeaSubmission(
            id="idea-gapi-01",
            submission_code="IDEA-2024-1001",
            raw_title="Lightweight alloy brake lever",
            raw_description="Reduce weight and save ₹3.0/veh.",
            raw_claimed_saving_per_veh=3.0,
            target_vehicle_id="veh-gapi-spl",
            target_model_id="SPLENDOR_PLUS",
            target_part_id="part-gapi-brk",
            extracted_part_number="53100-KTR-900",
            decision_state=IdeaDecisionState.SUBMITTED.value,
            evidence_state=ImplementationEvidenceState.NO_EVIDENCE_FOUND.value,
        )

        opp = IdeaOpportunityEvaluation(
            idea_id="idea-gapi-01",
            current_piece_cost_inr=50.0,
            proposed_piece_cost_inr=47.0,
            saving_per_vehicle_inr=3.0,
            applicable_annual_volume=1000000,
            gross_annual_opportunity_inr=3000000.0,
            net_opportunity_inr=3000000.0,
            provenance_hash="mock-hash-api",
        )

        session.add_all([pf, veh, mod, var, gen, my, sub, assy, comp, part, idea, opp])
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_governance_api_flow(override_governance_client: AsyncClient, auth_headers: dict):
    # 1. Sync review item
    sync_resp = await override_governance_client.post(
        "/api/v1/governance/sync/idea-gapi-01",
        headers=auth_headers,
    )
    assert sync_resp.status_code == 200
    sync_data = sync_resp.json()
    assert sync_data["is_safety_critical"] is True
    assert sync_data["review_priority"] == "CRITICAL_P0"

    # 2. List queue
    queue_resp = await override_governance_client.get(
        "/api/v1/governance/queue",
        headers=auth_headers,
    )
    assert queue_resp.status_code == 200
    items = queue_resp.json()
    assert len(items) >= 1

    # 3. Perform Review Action (Approve)
    action_resp = await override_governance_client.post(
        "/api/v1/governance/action/idea-gapi-01",
        json={"action_type": "APPROVE", "comments": "Approved after material test validation."},
        headers=auth_headers,
    )
    assert action_resp.status_code == 200
    action_data = action_resp.json()
    assert action_data["review_status"] == "APPROVED"
    assert action_data["final_decision"] == "APPROVED"

    # 4. Get High-Value Business Case Detail View
    case_resp = await override_governance_client.get(
        "/api/v1/governance/review-case/idea-gapi-01",
        headers=auth_headers,
    )
    assert case_resp.status_code == 200
    case_data = case_resp.json()
    assert case_data["idea_id"] == "idea-gapi-01"
    assert case_data["dimensions"]["human_review_status"] == "APPROVED"
    assert case_data["financial_opportunity"]["gross_annual_opportunity_inr"] == 3000000.0
    assert len(case_data["review_actions_history"]) >= 1
