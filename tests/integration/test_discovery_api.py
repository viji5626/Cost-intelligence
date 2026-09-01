"""
Integration Tests for Discovery API Endpoints
"""

from datetime import date
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.services.retrieval.retrieval_service import RetrievalService
from database.models.engineering_change import EngineeringChange
from database.models.ideathon import IdeaSubmission
from database.models.part_bom import Assembly, BomItem, Component, Part, Subsystem
from database.models.vehicle_hierarchy import ModelGeneration, ModelYear, ProductFamily, Vehicle, VehicleModel, VehicleVariant


@pytest.fixture
async def override_discovery_client():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_test_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db

    async with session_maker() as session:
        # Seed hierarchy & parts
        pf = ProductFamily(id="pf-dapi-100", family_code="MOTORCYCLES_100CC", name="100cc Motorcycles")
        veh = Vehicle(id="veh-dapi-spl", vehicle_code="SPLENDOR", name="Splendor", product_family_id="pf-dapi-100")
        mod = VehicleModel(id="mod-dapi-spl", model_code="SPLENDOR_PLUS", name="Splendor Plus", vehicle_id="veh-dapi-spl")
        var = VehicleVariant(id="var-dapi-spl", variant_code="SPL_DRUM", name="Splendor Plus Drum", model_id="mod-dapi-spl")
        gen = ModelGeneration(id="gen-dapi-spl", generation_code="SPL_G1", name="Gen 1", variant_id="var-dapi-spl", start_year=2022)
        my = ModelYear(id="my-dapi-spl", year_code="SPL_2024", generation_id="gen-dapi-spl", calendar_year=2024)

        sub = Subsystem(id="sub-dapi-eng", code="ENGINE", name="Engine")
        assy = Assembly(id="assy-dapi-head", subsystem_id="sub-dapi-eng", code="CYLINDER_HEAD", name="Cylinder Head Assembly")
        comp = Component(id="comp-dapi-head", assembly_id="assy-dapi-head", code="CYL_HEAD_COVER", name="Cylinder Head Cover Component")
        part = Part(id="part-dapi-head", component_id="comp-dapi-head", part_number="11100-KCC-900", part_name="Cylinder Head Cover")
        bom = BomItem(id="bom-dapi-01", model_year_id="my-dapi-spl", part_id="part-dapi-head", quantity_per_vehicle=1.0)

        ecn = EngineeringChange(
            id="ecn-dapi-01",
            ecn_number="ECN-2024-0010",
            title="Reduce wall thickness of 11100-KCC-900 by 0.7mm",
            description="Reduced wall thickness from 3.5mm to 2.8mm on 11100-KCC-900.",
            release_date=date(2027, 6, 1),
            change_category="COST_REDUCTION",
            status="RELEASED",
            affected_part_id="part-dapi-head",
        )

        idea = IdeaSubmission(
            id="idea-dapi-01",
            submission_code="IDEA-2024-0099",
            raw_title="Reduce cylinder head cover thickness on Splendor Plus",
            raw_description="High mass on 11100-KCC-900. Reduce wall thickness by 0.7mm.",
            target_vehicle_id="veh-dapi-spl",
            target_model_id="SPLENDOR_PLUS",
            target_part_id="part-dapi-head",
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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_evaluate_idea_api(override_discovery_client: AsyncClient, auth_headers: dict):
    response = await override_discovery_client.post(
        "/api/v1/discovery/evaluate-idea/idea-dapi-01",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["evidence_state"] == "IMPLEMENTED"
    assert data["confidence_score"] >= 0.85
    assert len(data["discovered_evidences"]) >= 1


@pytest.mark.asyncio
async def test_cross_model_summary_api(override_discovery_client: AsyncClient, auth_headers: dict):
    response = await override_discovery_client.get(
        "/api/v1/discovery/cross-model-summary/11100-KCC-900",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["part_number"] == "11100-KCC-900"
    assert data["total_applicable_models"] >= 1
    assert "Splendor Plus" in data["sibling_models_sharing_part"]
