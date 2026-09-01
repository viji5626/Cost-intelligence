"""
Integration Tests for Hierarchy API Endpoints
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base, get_db
from backend.app.main import app
from database.models.plant_opex import Plant
from database.models.vehicle_hierarchy import ProductFamily, Vehicle, VehicleModel
from database.models.part_bom import Part, Subsystem, Assembly, Component


@pytest.fixture
async def override_db_client():
    """Yields an async HTTP test client using an in-memory SQLite database."""
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_test_db():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db

    # Seed initial test data
    async with session_maker() as session:
        p = Plant(id="plt-01", plant_code="PLT-HAR", name="Haridwar Plant", location="Haridwar", state="UK")
        pf = ProductFamily(id="pf-01", family_code="PF-COMM", name="Commuter")
        v = Vehicle(id="v-01", vehicle_code="V-SPL", name="Splendor", product_family_id=pf.id)
        vm = VehicleModel(id="vm-01", model_code="VM-SPLP", name="Splendor+", vehicle_id=v.id)
        sub = Subsystem(id="sub-01", code="SUB-CHAS", name="Chassis")
        asm = Assembly(id="asm-01", code="ASM-SWING", name="Swingarm", subsystem_id=sub.id)
        comp = Component(id="comp-01", code="COMP-BUSH", name="Bush", assembly_id=asm.id)
        part = Part(id="prt-01", part_number="52101KCC900", part_name="Swingarm Bush", component_id=comp.id)
        session.add_all([p, pf, v, vm, sub, asm, comp, part])
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_get_master_data_summary(override_db_client: AsyncClient, auth_headers: dict):
    response = await override_db_client.get(
        "/api/v1/hierarchy/summary",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["plants"] >= 1
    assert data["product_families"] >= 1
    assert data["vehicles"] >= 1
    assert data["parts"] >= 1


@pytest.mark.asyncio
async def test_get_part_lineage_api(override_db_client: AsyncClient, auth_headers: dict):
    response = await override_db_client.get(
        "/api/v1/hierarchy/parts/prt-01/lineage",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["part_number"] == "52101KCC900"
    assert data["component"]["name"] == "Bush"
    assert data["assembly"]["name"] == "Swingarm"
    assert data["subsystem"]["name"] == "Chassis"
