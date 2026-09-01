"""
Integration Tests for Ingestion API Endpoints
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base, get_db
from backend.app.main import app
from database.models.plant_opex import Plant


@pytest.fixture
async def override_ingestion_client():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_test_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db

    async with session_maker() as session:
        plant = Plant(id="plt-01", plant_code="PLANT-HAR", name="Haridwar Plant", location="Haridwar", state="UK")
        session.add(plant)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_get_templates_api(override_ingestion_client: AsyncClient, auth_headers: dict):
    response = await override_ingestion_client.get(
        "/api/v1/ingestion/templates/PLANT_OPEX",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "plant_code" in data
    assert "total_opex" in data


@pytest.mark.asyncio
async def test_upload_dry_run_api(override_ingestion_client: AsyncClient, auth_headers: dict):
    csv_content = (
        "plant_code,period,production_quantity,electricity_kwh,total_opex\n"
        "PLANT-HAR,2024-04-01,120000,2800000,60000000\n"
    ).encode("utf-8")

    files = {"file": ("test_opex.csv", csv_content, "text/csv")}
    data = {"target": "PLANT_OPEX", "dry_run": "true"}

    response = await override_ingestion_client.post(
        "/api/v1/ingestion/upload",
        headers=auth_headers,
        data=data,
        files=files,
    )
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "COMPLETED"
    assert res_json["total_rows"] == 1
    assert res_json["valid_rows"] == 1
