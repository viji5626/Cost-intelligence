"""
Integration Tests for Plant OPEX and Benchmarking API Endpoints
"""

from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base, get_db
from backend.app.main import app
from database.models.plant_opex import OpexRecord, Plant


@pytest.fixture
async def override_opex_client():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_test_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db

    async with session_maker() as session:
        p1 = Plant(
            id="plt-har",
            plant_code="PLANT-HAR",
            name="Haridwar Plant",
            location="Haridwar",
            state="UK",
            annual_capacity_vehicles=1200000,
            manufacturing_scope="FULL_VEHICLE_ASSEMBLY",
            grid_tariff_inr_kwh=Decimal("7.50"),
        )
        p2 = Plant(
            id="plt-dha",
            plant_code="PLANT-DHA",
            name="Dharuhera Plant",
            location="Dharuhera",
            state="HR",
            annual_capacity_vehicles=1200000,
            manufacturing_scope="FULL_VEHICLE_ASSEMBLY",
            grid_tariff_inr_kwh=Decimal("7.50"),
        )
        session.add_all([p1, p2])
        await session.flush()

        from datetime import date

        r1 = OpexRecord(
            plant_id="plt-har",
            period=date(2024, 4, 1),
            production_quantity=100000,
            electricity_kwh=Decimal("2600000.00"),
            electricity_cost=Decimal("19500000.00"),
            water_kl=Decimal("20000.00"),
            water_cost=Decimal("1200000.00"),
            gas_consumption_nm3=Decimal("50000.00"),
            gas_cost=Decimal("2500000.00"),
            compressed_air_nm3=Decimal("300000.00"),
            compressed_air_cost=Decimal("1500000.00"),
            waste_quantity_mt=Decimal("150.00"),
            waste_cost=Decimal("600000.00"),
            labor_cost=Decimal("20000000.00"),
            maintenance_cost=Decimal("10000000.00"),
            other_opex=Decimal("4200000.00"),
            total_opex=Decimal("59500000.00"),
        )
        session.add(r1)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_get_plant_kpis_api(override_opex_client: AsyncClient, auth_headers: dict):
    response = await override_opex_client.get(
        "/api/v1/opex/kpis/plt-har",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["plant_code"] == "PLANT-HAR"
    assert data["kwh_per_vehicle"] == "26.0000"
    assert data["total_opex_per_vehicle"] == "595.0000"


@pytest.mark.asyncio
async def test_post_benchmark_compare_api(override_opex_client: AsyncClient, auth_headers: dict):
    payload = {
        "target_plant_id": "plt-har",
        "period": "2024-04-01",
        "mode": "MANAGEMENT_TARGET",
        "manual_target_opex_per_veh": "500.00",
    }
    response = await override_opex_client.post(
        "/api/v1/opex/benchmark/compare",
        headers=auth_headers,
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["benchmark_mode"] == "MANAGEMENT_TARGET"
    assert data["benchmark_total_opex_per_vehicle"] == "500.00"
    assert data["variance"]["total_gap_per_vehicle"] == "95.0000"
    assert "calculation_hash" in data


@pytest.mark.asyncio
async def test_get_opex_summary_api(override_opex_client: AsyncClient, auth_headers: dict):
    response = await override_opex_client.get(
        "/api/v1/opex/summary",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["plant_code"] == "PLANT-HAR"
