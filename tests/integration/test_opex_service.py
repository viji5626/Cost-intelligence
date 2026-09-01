"""
Integration Tests for Plant OPEX Service
"""

from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base
from backend.app.services.opex.opex_service import PlantOpexService
from calculations.opex.models import BenchmarkMode
from database.models.plant_opex import OpexRecord, Plant


@pytest.fixture
async def opex_test_session():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        # Seed Plant A (Haridwar)
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
        # Seed Plant B (Dharuhera)
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

        # Seed OPEX records
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
            total_opex=Decimal("59500000.00"),  # ₹595/veh
        )
        r2 = OpexRecord(
            plant_id="plt-dha",
            period=date(2024, 4, 1),
            production_quantity=95000,
            electricity_kwh=Decimal("2280000.00"),
            electricity_cost=Decimal("17100000.00"),
            water_kl=Decimal("19000.00"),
            water_cost=Decimal("1140000.00"),
            gas_consumption_nm3=Decimal("47500.00"),
            gas_cost=Decimal("2375000.00"),
            compressed_air_nm3=Decimal("285000.00"),
            compressed_air_cost=Decimal("1425000.00"),
            waste_quantity_mt=Decimal("140.00"),
            waste_cost=Decimal("570000.00"),
            labor_cost=Decimal("19000000.00"),
            maintenance_cost=Decimal("8000000.00"),
            other_opex=Decimal("3500000.00"),
            total_opex=Decimal("53110000.00"),  # ₹559.0526/veh
        )
        session.add_all([r1, r2])
        await session.commit()
        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_get_plant_kpis_for_period(opex_test_session: AsyncSession):
    kpis = await PlantOpexService.get_plant_kpis_for_period(opex_test_session, "plt-har", "2024-04-01")
    assert kpis is not None
    assert kpis.plant_code == "PLANT-HAR"
    assert kpis.production_quantity == 100000
    assert kpis.total_opex_per_vehicle == Decimal("595.0000")


@pytest.mark.asyncio
async def test_run_benchmark_analysis_integration(opex_test_session: AsyncSession):
    bench = await PlantOpexService.run_benchmark_analysis(
        session=opex_test_session,
        target_plant_id="plt-har",
        period_str="2024-04-01",
        mode=BenchmarkMode.BEST_COMPARABLE,
        persist_record=True,
    )
    assert bench is not None
    assert bench.target_plant_name == "Haridwar Plant"
    assert "Dharuhera" in bench.benchmark_source_name
    assert bench.variance.total_gap_per_vehicle > Decimal("0.0")
    assert bench.gross_annual_opportunity_inr > Decimal("0.0")
