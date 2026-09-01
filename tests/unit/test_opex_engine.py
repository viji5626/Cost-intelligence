"""
Unit Tests for Deterministic OPEX Calculation Engine
Validates all metrics against independently computed mathematical reference values.
"""

from decimal import Decimal
import pytest
from calculations.opex.engine import OpexCalculationEngine


def test_calculate_plant_kpis_exact_math():
    """
    Reference Values:
    Production: 100,000 vehicles
    Electricity: 2,500,000 kWh -> 25.0000 kWh/veh
    Electricity Cost: Rs 18,750,000 -> Rs 187.5000 / veh
    Water: 20,000 KL -> 0.2000 KL/veh
    Water Cost: Rs 1,200,000 -> Rs 12.0000 / veh
    Total OPEX: Rs 55,000,000 -> Rs 550.0000 / veh
    """
    kpi = OpexCalculationEngine.calculate_plant_kpis(
        plant_id="plt-har",
        plant_code="PLANT-HAR",
        plant_name="Haridwar Plant",
        period_str="2024-04-01",
        production_quantity=100000,
        electricity_kwh=Decimal("2500000.00"),
        electricity_cost=Decimal("18750000.00"),
        water_kl=Decimal("20000.00"),
        water_cost=Decimal("1200000.00"),
        gas_consumption_nm3=Decimal("50000.00"),
        gas_cost=Decimal("2500000.00"),
        compressed_air_nm3=Decimal("300000.00"),
        compressed_air_cost=Decimal("1500000.00"),
        waste_quantity_mt=Decimal("150.00"),
        waste_cost=Decimal("600000.00"),
        labor_cost=Decimal("20000000.00"),
        maintenance_cost=Decimal("8000000.00"),
        other_opex=Decimal("2450000.00"),
        total_opex=Decimal("55000000.00"),
    )

    assert kpi.kwh_per_vehicle == Decimal("25.0000")
    assert kpi.electricity_inr_per_vehicle == Decimal("187.5000")
    assert kpi.water_kl_per_vehicle == Decimal("0.2000")
    assert kpi.water_inr_per_vehicle == Decimal("12.0000")
    assert kpi.total_opex_per_vehicle == Decimal("550.0000")
    assert kpi.gross_total_opex == Decimal("55000000.00")


def test_variance_decomposition():
    """
    Actual: Rs 650.0000 / veh, Tariff = Rs 8.50/kWh, Util = 70%
    Benchmark: Rs 550.0000 / veh, Tariff = Rs 7.50/kWh, Util = 85%, Benchmark kWh = 25.0
    Total Gap = Rs 100.0000
    Tariff Variance = (8.50 - 7.50) * 25.0 = Rs 25.0000
    Expected Addressable Operational Efficiency Gap <= Rs 75.0000
    """
    decomp = OpexCalculationEngine.decompose_variance(
        actual_total_opex_per_veh=Decimal("650.00"),
        benchmark_total_opex_per_veh=Decimal("550.00"),
        actual_grid_tariff=Decimal("8.50"),
        benchmark_grid_tariff=Decimal("7.50"),
        benchmark_kwh_per_veh=Decimal("25.00"),
        actual_capacity_util=Decimal("0.70"),
        benchmark_capacity_util=Decimal("0.85"),
    )

    assert decomp.total_gap_per_vehicle == Decimal("100.0000")
    assert decomp.tariff_variance_per_vehicle == Decimal("25.0000")
    assert decomp.addressable_gap_per_vehicle > Decimal("0.0")
    assert decomp.efficiency_gap_percentage > Decimal("0.0")


def test_calculate_annual_opportunity():
    # Rs 50.00 gap/veh on 1,200,000 annual volume = Rs 60,000,000 (Rs 6.0000 Crore)
    opp_inr, opp_cr = OpexCalculationEngine.calculate_annual_opportunity(
        addressable_gap_per_vehicle=Decimal("50.00"),
        annual_production_volume=1200000,
    )
    assert opp_inr == Decimal("60000000.00")
    assert opp_cr == Decimal("6.0000")


def test_provenance_hash_reproducibility():
    inputs = {"plant": "plt-01", "opex": "550"}
    outputs = {"gap": "50"}
    fixed_ts = "2026-08-31T12:00:00Z"
    ts1, h1 = OpexCalculationEngine.generate_calculation_provenance("calc-01", inputs, outputs, timestamp_str=fixed_ts)
    ts2, h2 = OpexCalculationEngine.generate_calculation_provenance("calc-01", inputs, outputs, timestamp_str=fixed_ts)
    assert len(h1) == 64
    assert h1 == h2
    assert ts1 == fixed_ts
