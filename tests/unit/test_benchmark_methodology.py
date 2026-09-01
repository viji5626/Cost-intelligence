"""
Unit Tests for Benchmark Methodology Domain Engine
Validates multi-factor comparability index and verifies that lowest absolute OPEX is not blindly chosen.
"""

from decimal import Decimal
from calculations.opex.benchmark_methodology import BenchmarkMethodology
from calculations.opex.engine import OpexCalculationEngine
from calculations.opex.models import (
    BenchmarkMode,
    ComparabilityWeights,
    PlantKpiMetrics,
)


def _mock_kpi(plant_id: str, code: str, name: str, opex_per_veh: Decimal, kwh_per_veh: Decimal, vol: int) -> PlantKpiMetrics:
    return PlantKpiMetrics(
        plant_id=plant_id,
        plant_code=code,
        plant_name=name,
        period="2024-04-01",
        production_quantity=vol,
        kwh_per_vehicle=kwh_per_veh,
        electricity_inr_per_vehicle=kwh_per_veh * Decimal("7.5"),
        water_kl_per_vehicle=Decimal("0.20"),
        water_inr_per_vehicle=Decimal("12.0"),
        gas_nm3_per_vehicle=Decimal("0.5"),
        gas_inr_per_vehicle=Decimal("25.0"),
        compressed_air_nm3_per_vehicle=Decimal("3.0"),
        compressed_air_inr_per_vehicle=Decimal("15.0"),
        waste_inr_per_vehicle=Decimal("6.0"),
        labor_inr_per_vehicle=Decimal("200.0"),
        maintenance_inr_per_vehicle=Decimal("80.0"),
        other_inr_per_vehicle=Decimal("24.5"),
        total_opex_per_vehicle=opex_per_veh,
        gross_total_opex=opex_per_veh * Decimal(str(vol)),
    )


def test_comparability_score_calculation():
    # Target: Full assembly, 100k vol, 3 shifts
    # Peer 1 (identical): Full assembly, 100k vol, 3 shifts -> score ~ 1.00
    # Peer 2 (different): Partial assembly, 20k vol, 1 shift -> score much lower
    p1 = BenchmarkMethodology.calculate_comparability_score(
        target_scope="FULL_VEHICLE_ASSEMBLY",
        target_volume=100000,
        target_shifts=3,
        target_capacity=1200000,
        target_tariff=Decimal("7.50"),
        peer_scope="FULL_VEHICLE_ASSEMBLY",
        peer_volume=100000,
        peer_shifts=3,
        peer_capacity=1200000,
        peer_tariff=Decimal("7.50"),
        peer_total_opex_per_veh=Decimal("520.00"),
        candidate_plant_id="plt-02",
        candidate_plant_code="PLANT-DHA",
        candidate_plant_name="Dharuhera",
    )
    assert p1.comparability_index == Decimal("1.0000")

    p2 = BenchmarkMethodology.calculate_comparability_score(
        target_scope="FULL_VEHICLE_ASSEMBLY",
        target_volume=100000,
        target_shifts=3,
        target_capacity=1200000,
        target_tariff=Decimal("7.50"),
        peer_scope="ASSEMBLY_ONLY",
        peer_volume=25000,
        peer_shifts=1,
        peer_capacity=400000,
        peer_tariff=Decimal("9.00"),
        peer_total_opex_per_veh=Decimal("300.00"),  # Low OPEX because assembly only!
        candidate_plant_id="plt-03",
        candidate_plant_code="PLANT-HAL",
        candidate_plant_name="Halol",
    )
    assert p2.comparability_index < Decimal("0.6000")


def test_best_comparable_does_not_blindly_pick_lowest_absolute_opex():
    """
    Demonstrates domain rule:
    Plant A (Haridwar, Target): ₹600/veh, Full Assembly, 100k vol.
    Peer B (Dharuhera): ₹520/veh, Full Assembly, 95k vol (High comparability, superior efficiency).
    Peer C (Halol Assembly-only): ₹350/veh, Assembly-only, 20k vol (Lowest absolute OPEX, but low comparability).

    Best Comparable MUST pick Peer B (Dharuhera), NOT Peer C!
    """
    target_kpi = _mock_kpi("plt-har", "PLANT-HAR", "Haridwar", Decimal("600.00"), Decimal("26.0"), 100000)
    peer_b = _mock_kpi("plt-dha", "PLANT-DHA", "Dharuhera", Decimal("520.00"), Decimal("24.0"), 95000)
    peer_c = _mock_kpi("plt-hal", "PLANT-HAL", "Halol", Decimal("350.00"), Decimal("15.0"), 20000)

    peer_meta = {
        "plt-dha": {"scope": "FULL_VEHICLE_ASSEMBLY", "capacity": 1200000, "shifts": 3, "tariff": Decimal("7.50")},
        "plt-hal": {"scope": "ASSEMBLY_ONLY", "capacity": 300000, "shifts": 1, "tariff": Decimal("8.50")},
    }

    result = BenchmarkMethodology.evaluate_benchmark_opportunity(
        target_plant_id="plt-har",
        target_plant_name="Haridwar",
        target_kpi=target_kpi,
        target_scope="FULL_VEHICLE_ASSEMBLY",
        target_capacity=1200000,
        target_shifts=3,
        target_tariff=Decimal("7.50"),
        peer_kpis=[peer_b, peer_c],
        peer_metadata_map=peer_meta,
        mode=BenchmarkMode.BEST_COMPARABLE,
    )

    # Must select Dharuhera as the best comparable peer
    assert "Dharuhera" in result.benchmark_source_name
    assert result.benchmark_total_opex_per_vehicle == Decimal("520.00")
    assert result.variance.total_gap_per_vehicle == Decimal("80.0000")
    assert result.gross_annual_opportunity_crores > Decimal("0.0")


def test_management_target_mode():
    target_kpi = _mock_kpi("plt-har", "PLANT-HAR", "Haridwar", Decimal("600.00"), Decimal("26.0"), 100000)
    result = BenchmarkMethodology.evaluate_benchmark_opportunity(
        target_plant_id="plt-har",
        target_plant_name="Haridwar",
        target_kpi=target_kpi,
        target_scope="FULL_VEHICLE_ASSEMBLY",
        target_capacity=1200000,
        target_shifts=3,
        target_tariff=Decimal("7.50"),
        peer_kpis=[],
        peer_metadata_map={},
        mode=BenchmarkMode.MANAGEMENT_TARGET,
        manual_target_opex_per_veh=Decimal("500.00"),
    )
    assert result.benchmark_total_opex_per_vehicle == Decimal("500.00")
    assert result.variance.total_gap_per_vehicle == Decimal("100.0000")
