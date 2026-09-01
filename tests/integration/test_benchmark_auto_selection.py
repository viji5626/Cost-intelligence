"""
Phase 10 — Benchmark Auto-Selection Regression Tests (LEVEL 1)
==============================================================
Correction 3 regression: validates that benchmark peer selection is ALWAYS
performed automatically by the backend BenchmarkMethodology engine.

Tests:
  1. BEST_COMPARABLE mode selects best peer automatically
  2. Request without benchmark_plant_id succeeds (200, not 422)
  3. Invalid mode 'BEST_IN_GROUP' raises Pydantic 422 at HTTP layer
  4. BenchmarkMode.BEST_COMPARABLE maps to "Best Comparable Peer:" source name

Test database: sqlite+aiosqlite:///:memory:
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.database import Base
from backend.app.services.opex.opex_service import PlantOpexService
from calculations.opex.benchmark_methodology import BenchmarkMethodology
from calculations.opex.models import BenchmarkMode
from database.models.plant_opex import OpexRecord, Plant


# ---------------------------------------------------------------------------
# Fixture: two-plant OPEX setup (Plant-A higher, Plant-B lower OPEX)
# ---------------------------------------------------------------------------

@pytest.fixture
async def benchmark_session():
    """
    In-memory session with Plant-A-DEMO (higher OPEX) and Plant-B-DEMO (lower OPEX).
    Plant-B is the expected auto-selected benchmark for Plant-A.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        plant_a = Plant(
            id="plant-a-demo",
            plant_code="PLANT-A-DEMO",
            name="Plant A Demo",
            location="Haridwar",
            state="UK",
            annual_capacity_vehicles=1_200_000,
            manufacturing_scope="FULL_VEHICLE_ASSEMBLY",
            grid_tariff_inr_kwh=Decimal("7.50"),
        )
        plant_b = Plant(
            id="plant-b-demo",
            plant_code="PLANT-B-DEMO",
            name="Plant B Demo",
            location="Dharuhera",
            state="HR",
            annual_capacity_vehicles=1_200_000,
            manufacturing_scope="FULL_VEHICLE_ASSEMBLY",
            grid_tariff_inr_kwh=Decimal("7.40"),
        )
        session.add_all([plant_a, plant_b])
        await session.flush()

        # Plant A: ₹595/veh (higher)
        opex_a = OpexRecord(
            plant_id="plant-a-demo",
            period=date(2024, 4, 1),
            production_quantity=100_000,
            electricity_kwh=Decimal("4250000.00"),
            electricity_cost=Decimal("31875000.00"),
            water_kl=Decimal("35000.00"),
            water_cost=Decimal("875000.00"),
            gas_consumption_nm3=Decimal("120000.00"),
            gas_cost=Decimal("5000000.00"),
            compressed_air_nm3=Decimal("345000.00"),
            compressed_air_cost=Decimal("1520000.00"),
            is_compressor_power_embedded=True,
            waste_quantity_mt=Decimal("150.00"),
            waste_cost=Decimal("600000.00"),
            labor_cost=Decimal("20000000.00"),
            maintenance_cost=Decimal("10000000.00"),
            other_opex=Decimal("4200000.00"),
            total_opex=Decimal("59500000.00"),
        )
        # Plant B: ₹520/veh (lower — should be auto-selected as best peer)
        opex_b = OpexRecord(
            plant_id="plant-b-demo",
            period=date(2024, 4, 1),
            production_quantity=95_000,
            electricity_kwh=Decimal("3610000.00"),
            electricity_cost=Decimal("26714000.00"),
            water_kl=Decimal("29000.00"),
            water_cost=Decimal("754000.00"),
            gas_consumption_nm3=Decimal("100000.00"),
            gas_cost=Decimal("4000000.00"),
            compressed_air_nm3=Decimal("275500.00"),
            compressed_air_cost=Decimal("1235000.00"),
            is_compressor_power_embedded=True,
            waste_quantity_mt=Decimal("140.00"),
            waste_cost=Decimal("560000.00"),
            labor_cost=Decimal("17000000.00"),
            maintenance_cost=Decimal("8000000.00"),
            other_opex=Decimal("3100000.00"),
            total_opex=Decimal("49400000.00"),
        )
        session.add_all([opex_a, opex_b])
        await session.commit()

        yield session

    await engine.dispose()


# ---------------------------------------------------------------------------
# Test 1 — BEST_COMPARABLE auto-selects Plant-B
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_best_comparable_auto_selects_plant_b(benchmark_session: AsyncSession):
    """
    BEST_COMPARABLE mode must automatically select Plant-B (lower OPEX, same scope).
    benchmark_plant_id is NOT provided as input — backend owns the selection entirely.
    """
    result = await PlantOpexService.run_benchmark_analysis(
        session=benchmark_session,
        target_plant_id="plant-a-demo",
        period_str="2024-04-01",
        mode=BenchmarkMode.BEST_COMPARABLE,
        # benchmark_plant_id NOT passed — auto-selection only
    )
    assert result is not None, "run_benchmark_analysis must return a result"
    assert float(result.gross_annual_opportunity_inr) > 0, (
        "Gross annual opportunity must be positive: Plant-A OPEX > Plant-B OPEX"
    )
    assert result.benchmark_comparability_index is not None
    assert float(result.benchmark_comparability_index) > 0, (
        "Comparability index must be positive"
    )
    # Auto-selection source name must identify the engine's choice
    assert "Best Comparable Peer" in result.benchmark_source_name, (
        f"benchmark_source_name must contain 'Best Comparable Peer', got: '{result.benchmark_source_name}'"
    )
    # Plant-B should be identified (by name or code)
    assert "Plant B Demo" in result.benchmark_source_name or "PLANT-B-DEMO" in result.benchmark_source_name, (
        f"Plant-B-DEMO should appear in benchmark_source_name, got: '{result.benchmark_source_name}'"
    )


# ---------------------------------------------------------------------------
# Test 2 — No benchmark_plant_id in request does NOT cause validation error
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_no_benchmark_plant_id_does_not_fail(benchmark_session: AsyncSession):
    """
    BenchmarkCompareRequest has no benchmark_plant_id field.
    Calling run_benchmark_analysis without it must succeed (200, not raise).
    """
    # This test verifies the service layer — no benchmark_plant_id kwarg
    result = await PlantOpexService.run_benchmark_analysis(
        session=benchmark_session,
        target_plant_id="plant-a-demo",
        period_str="2024-04-01",
        mode=BenchmarkMode.BEST_COMPARABLE,
    )
    assert result is not None, (
        "run_benchmark_analysis without benchmark_plant_id must succeed"
    )
    # Verify response does not contain a benchmark_plant_id field
    result_dict = result.model_dump()
    assert "benchmark_plant_id" not in result_dict, (
        "benchmark_plant_id must NOT appear in BenchmarkOpportunityResult — "
        "backend does not expose it as an input passthrough"
    )


# ---------------------------------------------------------------------------
# Test 3 — Invalid mode string fails Pydantic enum validation
# ---------------------------------------------------------------------------

def test_invalid_mode_best_in_group_is_rejected():
    """
    'BEST_IN_GROUP' is NOT a valid BenchmarkMode enum value.
    Pydantic must reject it, simulating the 422 that would occur at the HTTP layer.
    """
    import pytest
    from pydantic import ValidationError
    from pydantic import BaseModel

    class MockBenchmarkCompareRequest(BaseModel):
        target_plant_id: str
        mode: BenchmarkMode = BenchmarkMode.BEST_COMPARABLE

    with pytest.raises((ValueError, ValidationError)):
        MockBenchmarkCompareRequest(
            target_plant_id="plant-a-demo",
            mode="BEST_IN_GROUP",  # type: ignore[arg-type]  ← invalid value
        )


# ---------------------------------------------------------------------------
# Test 4 — BenchmarkMode.BEST_COMPARABLE produces "Best Comparable Peer:" source name
# ---------------------------------------------------------------------------

def test_best_comparable_mode_produces_correct_source_name():
    """
    Unit test: BenchmarkMethodology.evaluate_benchmark_opportunity() with
    BenchmarkMode.BEST_COMPARABLE must produce a benchmark_source_name that
    starts with 'Best Comparable Peer:' when a superior peer exists.
    """
    from calculations.opex.models import PlantKpiMetrics

    def make_kpi(plant_id, plant_code, plant_name, opex_pv, kwh_pv, water_pv) -> PlantKpiMetrics:
        """Construct a minimal PlantKpiMetrics with all required fields."""
        base = Decimal(opex_pv)
        return PlantKpiMetrics(
            plant_id=plant_id,
            plant_code=plant_code,
            plant_name=plant_name,
            period="2024-04-01",
            production_quantity=100_000,
            kwh_per_vehicle=Decimal(kwh_pv),
            electricity_inr_per_vehicle=Decimal(kwh_pv) * Decimal("7.50"),
            water_kl_per_vehicle=Decimal(water_pv),
            water_inr_per_vehicle=Decimal(water_pv) * Decimal("50"),
            gas_nm3_per_vehicle=Decimal("1.20"),
            gas_inr_per_vehicle=Decimal("50.00"),
            compressed_air_nm3_per_vehicle=Decimal("3.45"),
            compressed_air_inr_per_vehicle=Decimal("15.20"),
            waste_inr_per_vehicle=Decimal("6.00"),
            labor_inr_per_vehicle=Decimal("200.00"),
            maintenance_inr_per_vehicle=Decimal("100.00"),
            other_inr_per_vehicle=Decimal("42.00"),
            total_opex_per_vehicle=base,
            gross_total_opex=base * Decimal("100000"),
        )

    target_kpi = make_kpi("plant-a-demo", "PLANT-A-DEMO", "Plant A Demo", "595.00", "42.50", "0.35")
    peer_kpi = make_kpi("plant-b-demo", "PLANT-B-DEMO", "Plant B Demo", "520.00", "38.00", "0.31")

    peer_metadata_map = {
        "plant-b-demo": {
            "scope": "FULL_VEHICLE_ASSEMBLY",
            "shifts": 3,
            "capacity": 1_200_000,
            "tariff": Decimal("7.40"),
        }
    }

    result = BenchmarkMethodology.evaluate_benchmark_opportunity(
        target_plant_id="plant-a-demo",
        target_plant_name="Plant A Demo",
        target_kpi=target_kpi,
        target_scope="FULL_VEHICLE_ASSEMBLY",
        target_capacity=1_200_000,
        target_shifts=3,
        target_tariff=Decimal("7.50"),
        peer_kpis=[peer_kpi],
        peer_metadata_map=peer_metadata_map,
        mode=BenchmarkMode.BEST_COMPARABLE,
    )

    assert result.benchmark_source_name.startswith("Best Comparable Peer:"), (
        f"benchmark_source_name must start with 'Best Comparable Peer:', "
        f"got: '{result.benchmark_source_name}'"
    )

