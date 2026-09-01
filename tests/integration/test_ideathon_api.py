"""
Integration Tests for Ideathon API Endpoints
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base, get_db
from backend.app.main import app
from database.models.part_bom import Assembly, Component, Part, Subsystem
from database.models.vehicle_hierarchy import ProductFamily, Vehicle, VehicleModel


@pytest.fixture
async def override_ideathon_client():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_test_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db

    async with session_maker() as session:
        pf = ProductFamily(id="pf-01", family_code="MOTORCYCLES_100CC", name="100cc Motorcycles")
        veh = Vehicle(id="veh-01", vehicle_code="SPLENDOR", name="Splendor", product_family_id="pf-01")
        model = VehicleModel(id="vmod-01", model_code="SPLENDOR_PLUS", name="Splendor Plus", vehicle_id="veh-01")
        
        sub = Subsystem(id="sub-01", code="ENGINE", name="Engine")
        assy = Assembly(id="assy-01", subsystem_id="sub-01", code="CYLINDER_HEAD", name="Cylinder Head Assembly")
        comp = Component(id="comp-01", assembly_id="assy-01", code="CYL_HEAD_COVER", name="Cylinder Head Cover Component")
        part = Part(id="part-01", component_id="comp-01", part_number="11100-KCC-900", part_name="Cylinder Head Cover")
        session.add_all([pf, veh, model, sub, assy, comp, part])
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_submit_idea_api(override_ideathon_client: AsyncClient, auth_headers: dict):
    payload = {
        "title": "Reduce cylinder head cover thickness on Splendor Plus",
        "description": "Problem: High aluminum weight on 11100-KCC-900. Solution: Reduce thickness from 3.5mm to 2.8mm.",
        "submitter_employee_id": "EMP-9912",
        "claimed_saving_per_veh": "4.20",
    }
    response = await override_ideathon_client.post(
        "/api/v1/ideathon/submit",
        headers=auth_headers,
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["raw_title"] == "Reduce cylinder head cover thickness on Splendor Plus"
    assert data["extracted_part_number"] == "11100-KCC-900"
    assert data["decision_state"] == "SUBMITTED"
    assert data["evidence_state"] == "NOT_EVALUATED"


@pytest.mark.asyncio
async def test_list_ideas_and_review_queue_api(override_ideathon_client: AsyncClient, auth_headers: dict):
    # 1. Submit valid idea
    await override_ideathon_client.post(
        "/api/v1/ideathon/submit",
        headers=auth_headers,
        json={
            "title": "Splendor Plus handle weight reduction",
            "description": "Reduce handle weight on 11100-KCC-900 by 50g.",
        },
    )

    # 2. Submit ambiguous idea
    await override_ideathon_client.post(
        "/api/v1/ideathon/submit",
        headers=auth_headers,
        json={
            "title": "Unspecified body bracket simplification",
            "description": "Fastener optimization.",
        },
    )

    # 3. List ideas
    list_res = await override_ideathon_client.get("/api/v1/ideathon/ideas", headers=auth_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 2

    # 4. Check review queue
    review_res = await override_ideathon_client.get("/api/v1/ideathon/review-queue", headers=auth_headers)
    assert review_res.status_code == 200
    assert len(review_res.json()) >= 1
