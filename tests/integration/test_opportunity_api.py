"""
Integration Tests for Opportunity Evaluation & Simulation APIs
"""

from datetime import date
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base, get_db
from backend.app.main import app
from database.models.ideathon import IdeaSubmission
from database.models.part_bom import Assembly, BomItem, Component, ComponentCost, Part, Subsystem
from database.models.vehicle_hierarchy import ModelGeneration, ModelYear, ProductFamily, Vehicle, VehicleModel, VehicleVariant


@pytest.fixture
async def override_opportunity_client():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_test_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db

    async with session_maker() as session:
        pf = ProductFamily(id="pf-oapi-100", family_code="MOTORCYCLES_100CC", name="100cc Motorcycles")
        veh = Vehicle(id="veh-oapi-spl", vehicle_code="SPLENDOR", name="Splendor", product_family_id="pf-oapi-100")
        mod = VehicleModel(id="mod-oapi-spl", model_code="SPLENDOR_PLUS", name="Splendor Plus", vehicle_id="veh-oapi-spl")
        var = VehicleVariant(id="var-oapi-spl", variant_code="SPL_DRUM", name="Splendor Plus Drum", model_id="mod-oapi-spl")
        gen = ModelGeneration(id="gen-oapi-spl", generation_code="SPL_G1", name="Gen 1", variant_id="var-oapi-spl", start_year=2022)
        my = ModelYear(id="my-oapi-spl", year_code="SPL_2024", generation_id="gen-oapi-spl", calendar_year=2024, annual_volume_planned=1000000)

        sub = Subsystem(id="sub-oapi-eng", code="ENGINE", name="Engine")
        assy = Assembly(id="assy-oapi-head", subsystem_id="sub-oapi-eng", code="CYLINDER_HEAD", name="Cylinder Head Assembly")
        comp = Component(id="comp-oapi-head", assembly_id="assy-oapi-head", code="CYL_HEAD_COVER", name="Cylinder Head Cover Component")
        part = Part(id="part-oapi-head", component_id="comp-oapi-head", part_number="11100-KCC-900", part_name="Cylinder Head Cover")
        bom = BomItem(id="bom-oapi-01", model_year_id="my-oapi-spl", part_id="part-oapi-head", quantity_per_vehicle=1.0)

        cost = ComponentCost(
            id="cost-oapi-01",
            part_id="part-oapi-head",
            period_start=date(2024, 1, 1),
            total_cost=100.0,
            currency="INR",
        )

        idea = IdeaSubmission(
            id="idea-oapi-01",
            submission_code="IDEA-2024-0801",
            raw_title="Reduce cylinder head cover thickness",
            raw_description="Reduce thickness to save ₹4.0/veh.",
            raw_claimed_saving_per_veh=4.0,
            target_vehicle_id="veh-oapi-spl",
            target_model_id="SPLENDOR_PLUS",
            target_part_id="part-oapi-head",
            extracted_part_number="11100-KCC-900",
            decision_state="ACCEPTED_FOR_STUDY",
        )

        session.add_all([pf, veh, mod, var, gen, my, sub, assy, comp, part, bom, cost, idea])
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_evaluate_opportunity_api(override_opportunity_client: AsyncClient, auth_headers: dict):
    response = await override_opportunity_client.post(
        "/api/v1/opportunity/evaluate-idea/idea-oapi-01",
        json={"tooling_investment": 500000.0, "validation_investment": 100000.0},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CALCULATED"
    assert data["current_piece_cost_inr"] == 100.0
    assert data["proposed_piece_cost_inr"] == 96.0
    assert data["saving_per_vehicle_inr"] == 4.0
    assert data["applicable_annual_volume"] == 1000000
    assert data["gross_annual_opportunity_inr"] == 4000000.0
    assert data["net_opportunity_inr"] == 3400000.0
    assert data["payback_period_years"] == 0.15
    assert data["payback_period_months"] == 1.8


@pytest.mark.asyncio
async def test_simulate_opportunity_api(override_opportunity_client: AsyncClient, auth_headers: dict):
    response = await override_opportunity_client.post(
        "/api/v1/opportunity/simulate",
        json={
            "current_piece_cost": 250.0,
            "proposed_piece_cost": 240.0,
            "volumes_by_model": {"SPLENDOR_PLUS": 800000, "HF_DELUXE": 400000},
            "applicable_models": ["SPLENDOR_PLUS", "HF_DELUXE"],
            "tooling_investment": 1200000.0,
            "validation_investment": 300000.0,
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CALCULATED"
    assert data["saving_per_vehicle_inr"] == 10.0
    assert data["applicable_annual_volume"] == 1200000
    assert data["gross_annual_opportunity_inr"] == 12000000.0
    assert data["net_opportunity_inr"] == 10500000.0
    assert data["payback_period_years"] == 0.125
    assert data["payback_period_months"] == 1.5


@pytest.mark.asyncio
async def test_get_idea_opportunity_api(override_opportunity_client: AsyncClient, auth_headers: dict):
    # First evaluate
    await override_opportunity_client.post(
        "/api/v1/opportunity/evaluate-idea/idea-oapi-01",
        json={"tooling_investment": 200000.0},
        headers=auth_headers,
    )

    # Then retrieve
    response = await override_opportunity_client.get(
        "/api/v1/opportunity/idea/idea-oapi-01",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CALCULATED"
    assert data["gross_annual_opportunity_inr"] == 4000000.0
