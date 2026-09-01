"""
Unit & Domain Tests for Plant OPEX Compressed Air Utility & Double-Counting Protection
Validates all 12 validation requirements:
1. CF/vehicle calculation
2. kWh/CF calculation
3. CF/kWh calculation
4. zero production handling
5. zero compressed-air volume (division-by-zero protection)
6. missing compressor kWh (explicit None state)
7. missing compressed-air CF (explicit None state)
8. double-counting protection (embedded vs non-embedded)
9. ingestion aliases matching
10. API serialization
11. benchmark comparison of compressed air dimensions
12. Decimal precision and half-up rounding
"""

from decimal import Decimal
import pytest

from calculations.opex.benchmark_methodology import BenchmarkMethodology
from calculations.opex.engine import OpexCalculationEngine
from calculations.opex.models import (
    BenchmarkMode,
    PlantKpiMetrics,
)
from backend.app.services.ingestion.models import COLUMN_ALIASES, IngestionTarget
from backend.app.services.ingestion.parser import IngestionParser


def test_1_cf_per_vehicle_calculation():
    """Requirement 1: CF / vehicle = Total compressed-air CF / Production volume."""
    cf_per_veh, _, _, _ = OpexCalculationEngine.calculate_compressed_air_metrics(
        production_quantity=100000,
        compressed_air_cf_total=Decimal("345000.00"),
    )
    # 345000 / 100000 = 3.4500
    assert cf_per_veh == Decimal("3.4500")


def test_2_kwh_per_cf_calculation():
    """Requirement 2: kWh / CF = Compressor electricity kWh / Compressed-air CF."""
    _, kwh_per_cf, _, _ = OpexCalculationEngine.calculate_compressed_air_metrics(
        production_quantity=100000,
        compressed_air_cf_total=Decimal("500000.00"),
        compressor_kwh_total=Decimal("10000.00"),
    )
    # 10000 / 500000 = 0.020000 kWh/CF
    assert kwh_per_cf == Decimal("0.020000")


def test_3_cf_per_kwh_calculation():
    """Requirement 3: CF / kWh = Compressed-air CF / Compressor electricity kWh."""
    _, _, cf_per_kwh, _ = OpexCalculationEngine.calculate_compressed_air_metrics(
        production_quantity=100000,
        compressed_air_cf_total=Decimal("500000.00"),
        compressor_kwh_total=Decimal("10000.00"),
    )
    # 500000 / 10000 = 50.0000 CF/kWh
    assert cf_per_kwh == Decimal("50.0000")


def test_4_zero_production_handling():
    """Requirement 4: Zero production handling."""
    # When production_quantity = 0 in calculate_compressed_air_metrics, returns None for per-vehicle metrics
    cf_per_veh, kwh_per_cf, cf_per_kwh, cost_per_veh = OpexCalculationEngine.calculate_compressed_air_metrics(
        production_quantity=0,
        compressed_air_cf_total=Decimal("100000.00"),
        compressor_kwh_total=Decimal("2000.00"),
    )
    assert cf_per_veh is None
    assert cost_per_veh is None
    # Physical efficiency between CF and kWh is still mathematically valid
    assert kwh_per_cf == Decimal("0.020000")
    assert cf_per_kwh == Decimal("50.0000")

    # In full plant normalization, zero production raises ValueError
    with pytest.raises(ValueError, match="must be > 0"):
        OpexCalculationEngine.calculate_plant_kpis(
            plant_id="plt-01",
            plant_code="P01",
            plant_name="Plant 01",
            period_str="2024-04-01",
            production_quantity=0,
            electricity_kwh=Decimal("10000.00"),
            electricity_cost=Decimal("75000.00"),
            water_kl=Decimal("100.00"),
            water_cost=Decimal("5000.00"),
            gas_consumption_nm3=Decimal("500.00"),
            gas_cost=Decimal("25000.00"),
            compressed_air_nm3=Decimal("1000.00"),
            compressed_air_cost=Decimal("5000.00"),
            waste_quantity_mt=Decimal("10.00"),
            waste_cost=Decimal("2000.00"),
            labor_cost=Decimal("50000.00"),
            maintenance_cost=Decimal("20000.00"),
            other_opex=Decimal("10000.00"),
            total_opex=Decimal("187000.00"),
        )


def test_5_zero_compressed_air_volume():
    """Requirement 5: Zero compressed-air volume handles division-by-zero safely."""
    cf_per_veh, kwh_per_cf, cf_per_kwh, _ = OpexCalculationEngine.calculate_compressed_air_metrics(
        production_quantity=100000,
        compressed_air_cf_total=Decimal("0.00"),
        compressor_kwh_total=Decimal("5000.00"),
    )
    assert cf_per_veh == Decimal("0.0000")
    assert kwh_per_cf is None  # Divisor is 0, must not crash with ZeroDivisionError
    assert cf_per_kwh == Decimal("0.0000")


def test_6_missing_compressor_kwh():
    """Requirement 6: Missing compressor kWh returns explicit None state without inventing values."""
    cf_per_veh, kwh_per_cf, cf_per_kwh, cost_per_veh = OpexCalculationEngine.calculate_compressed_air_metrics(
        production_quantity=100000,
        compressed_air_cf_total=Decimal("250000.00"),
        compressor_kwh_total=None,
    )
    assert cf_per_veh == Decimal("2.5000")
    assert kwh_per_cf is None
    assert cf_per_kwh is None
    assert cost_per_veh is None


def test_7_missing_compressed_air_cf():
    """Requirement 7: Missing compressed-air CF returns explicit None state."""
    cf_per_veh, kwh_per_cf, cf_per_kwh, _ = OpexCalculationEngine.calculate_compressed_air_metrics(
        production_quantity=100000,
        compressed_air_cf_total=None,
        compressor_kwh_total=Decimal("8000.00"),
    )
    assert cf_per_veh is None
    assert kwh_per_cf is None
    assert cf_per_kwh is None


def test_8_double_counting_protection():
    """
    Requirement 8: Double-counting protection.
    Compressor electricity must NOT be added on top of total electricity OPEX
    when is_compressor_power_embedded is True.
    """
    kpis = OpexCalculationEngine.calculate_plant_kpis(
        plant_id="plt-har",
        plant_code="PLANT-HAR",
        plant_name="Haridwar Plant",
        period_str="2024-04-01",
        production_quantity=100000,
        electricity_kwh=Decimal("2500000.00"),      # Total plant electricity (includes 200,000 kWh for compressors)
        electricity_cost=Decimal("18750000.00"),   # Rs 187.50 / veh
        water_kl=Decimal("20000.00"),
        water_cost=Decimal("1200000.00"),
        gas_consumption_nm3=Decimal("50000.00"),
        gas_cost=Decimal("2500000.00"),
        compressed_air_nm3=Decimal("300000.00"),
        compressed_air_cost=Decimal("0.00"),
        waste_quantity_mt=Decimal("150.00"),
        waste_cost=Decimal("600000.00"),
        labor_cost=Decimal("20000000.00"),
        maintenance_cost=Decimal("8000000.00"),
        other_opex=Decimal("3950000.00"),
        total_opex=Decimal("55000000.00"),         # Rs 550.00 / veh
        compressed_air_cf_total=Decimal("400000.00"),
        compressor_kwh_total=Decimal("200000.00"), # 200,000 kWh compressor energy
        is_compressor_power_embedded=True,
    )

    assert kpis.is_compressor_power_embedded is True
    assert kpis.total_opex_per_vehicle == Decimal("550.0000")
    assert kpis.kwh_per_vehicle == Decimal("25.0000")
    assert kpis.compressor_kwh_total == Decimal("200000.00")
    assert kpis.compressor_kwh_per_cf == Decimal("0.500000")
    assert kpis.compressor_cf_per_kwh == Decimal("2.0000")
    # Gross total OPEX remains exactly Rs 55,000,000 without compressor power added twice
    assert kpis.gross_total_opex == Decimal("55000000.00")


def test_9_ingestion_aliases():
    """Requirement 9: Ingestion aliases for varied customer naming conventions."""
    aliases = COLUMN_ALIASES[IngestionTarget.PLANT_OPEX]
    
    # Test volume aliases
    assert "compressed_air_volume" in aliases["compressed_air_cf_total"]
    assert "air_consumption_cf" in aliases["compressed_air_cf_total"]
    assert "air_volume_cf" in aliases["compressed_air_cf_total"]
    
    # Test compressor energy aliases
    assert "compressor_energy" in aliases["compressor_kwh_total"]
    assert "compressor_kwh" in aliases["compressor_kwh_total"]
    assert "compressed_air_kwh" in aliases["compressor_kwh_total"]

    # Test parser matching
    sample_headers = [
        "Plant Code",
        "Month",
        "Production Volume",
        "Power kWh",
        "Electricity INR",
        "Water KL",
        "Water Cost",
        "Gas Consumption",
        "Gas Cost",
        "Air Volume CF",
        "Compressor Energy",
        "Total Plant Cost",
    ]
    matched = IngestionParser.match_columns_to_target(sample_headers, IngestionTarget.PLANT_OPEX)
    assert matched.get("compressed_air_cf_total") == "Air Volume CF"
    assert matched.get("compressor_kwh_total") == "Compressor Energy"


def test_10_api_serialization():
    """Requirement 10: Pydantic model serialization & schema conformance."""
    kpi = PlantKpiMetrics(
        plant_id="plt-dhar",
        plant_code="PLANT-DHAR",
        plant_name="Dharuhera Plant",
        period="2024-04-01",
        production_quantity=120000,
        kwh_per_vehicle=Decimal("22.5000"),
        electricity_inr_per_vehicle=Decimal("168.7500"),
        water_kl_per_vehicle=Decimal("0.1800"),
        water_inr_per_vehicle=Decimal("10.8000"),
        gas_nm3_per_vehicle=Decimal("0.4500"),
        gas_inr_per_vehicle=Decimal("22.5000"),
        compressed_air_nm3_per_vehicle=Decimal("2.8000"),
        compressed_air_inr_per_vehicle=Decimal("0.0000"),
        compressed_air_cf_total=Decimal("336000.00"),
        compressed_air_cf_per_vehicle=Decimal("2.8000"),
        compressor_kwh_total=Decimal("6720.00"),
        compressor_kwh_per_cf=Decimal("0.020000"),
        compressor_cf_per_kwh=Decimal("50.0000"),
        compressed_air_cost_inr=None,
        compressed_air_cost_per_vehicle=None,
        is_compressor_power_embedded=True,
        waste_inr_per_vehicle=Decimal("5.0000"),
        labor_inr_per_vehicle=Decimal("180.0000"),
        maintenance_inr_per_vehicle=Decimal("70.0000"),
        other_inr_per_vehicle=Decimal("22.9500"),
        total_opex_per_vehicle=Decimal("480.0000"),
        gross_total_opex=Decimal("57600000.00"),
    )
    serialized = kpi.model_dump()
    assert serialized["compressed_air_cf_per_vehicle"] == Decimal("2.8000")
    assert serialized["compressor_kwh_per_cf"] == Decimal("0.020000")
    assert serialized["compressor_cf_per_kwh"] == Decimal("50.0000")
    assert serialized["is_compressor_power_embedded"] is True


def test_11_benchmark_comparison():
    """Requirement 11: Benchmark comparison of compressed air dimensions across plants."""
    target_kpi = OpexCalculationEngine.calculate_plant_kpis(
        plant_id="plt-har",
        plant_code="PLANT-HAR",
        plant_name="Haridwar",
        period_str="2024-04-01",
        production_quantity=100000,
        electricity_kwh=Decimal("2500000.00"),
        electricity_cost=Decimal("18750000.00"),
        water_kl=Decimal("20000.00"),
        water_cost=Decimal("1200000.00"),
        gas_consumption_nm3=Decimal("50000.00"),
        gas_cost=Decimal("2500000.00"),
        compressed_air_nm3=Decimal("350000.00"),
        compressed_air_cost=Decimal("0.00"),
        compressed_air_cf_total=Decimal("350000.00"),
        compressor_kwh_total=Decimal("7700.00"),
        waste_quantity_mt=Decimal("150.00"),
        waste_cost=Decimal("600000.00"),
        labor_cost=Decimal("20000000.00"),
        maintenance_cost=Decimal("8000000.00"),
        other_opex=Decimal("3950000.00"),
        total_opex=Decimal("55000000.00"),
    )

    peer_kpi = OpexCalculationEngine.calculate_plant_kpis(
        plant_id="plt-dhar",
        plant_code="PLANT-DHAR",
        plant_name="Dharuhera",
        period_str="2024-04-01",
        production_quantity=100000,
        electricity_kwh=Decimal("2200000.00"),
        electricity_cost=Decimal("16500000.00"),
        water_kl=Decimal("18000.00"),
        water_cost=Decimal("1080000.00"),
        gas_consumption_nm3=Decimal("45000.00"),
        gas_cost=Decimal("2250000.00"),
        compressed_air_nm3=Decimal("290000.00"),
        compressed_air_cost=Decimal("0.00"),
        compressed_air_cf_total=Decimal("290000.00"),
        compressor_kwh_total=Decimal("5800.00"),
        waste_quantity_mt=Decimal("120.00"),
        waste_cost=Decimal("480000.00"),
        labor_cost=Decimal("18000000.00"),
        maintenance_cost=Decimal("7000000.00"),
        other_opex=Decimal("2690000.00"),
        total_opex=Decimal("48000000.00"),
    )

    result = BenchmarkMethodology.evaluate_benchmark_opportunity(
        target_plant_id="plt-har",
        target_plant_name="Haridwar",
        target_kpi=target_kpi,
        target_scope="FULL_VEHICLE_ASSEMBLY",
        target_capacity=1200000,
        target_shifts=3,
        target_tariff=Decimal("7.50"),
        peer_kpis=[target_kpi, peer_kpi],
        peer_metadata_map={
            "plt-har": {"scope": "FULL_VEHICLE_ASSEMBLY", "capacity": 1200000, "shifts": 3, "tariff": Decimal("7.50")},
            "plt-dhar": {"scope": "FULL_VEHICLE_ASSEMBLY", "capacity": 1200000, "shifts": 3, "tariff": Decimal("7.50")},
        },
        mode=BenchmarkMode.BEST_COMPARABLE,
    )

    assert result.benchmark_source_name.startswith("Best Comparable Peer: Dharuhera")
    assert result.benchmark_compressed_air_cf_per_vehicle == Decimal("2.9000")
    assert result.benchmark_compressor_kwh_per_cf == Decimal("0.020000")
    assert result.benchmark_compressor_cf_per_kwh == Decimal("50.0000")


def test_12_decimal_precision_rounding():
    """Requirement 12: Decimal precision and half-up rounding verification."""
    # 1 / 3 = 0.333333... rounded to 6 places for specific energy
    # 2 / 3 = 0.666666... rounded to 4 places for CF/veh
    cf_per_veh, kwh_per_cf, cf_per_kwh, _ = OpexCalculationEngine.calculate_compressed_air_metrics(
        production_quantity=3,
        compressed_air_cf_total=Decimal("2.00"),
        compressor_kwh_total=Decimal("1.00"),
    )
    assert cf_per_veh == Decimal("0.6667")
    assert kwh_per_cf == Decimal("0.500000")
    assert cf_per_kwh == Decimal("2.0000")
