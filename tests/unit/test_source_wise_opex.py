"""
Test Suite: Source-Wise Utilities & Deterministic OPEX Calculation Engine
Comprehensive unit tests covering Electricity, Water, Compressed Air, Natural Gas,
Double-Counting Accounting Safeguards, Benchmarking, and Ingestion Aliases.
"""

from decimal import Decimal
import pytest

from calculations.opex.engine import OpexCalculationEngine
from calculations.opex.benchmark_methodology import BenchmarkMethodology
from calculations.opex.models import (
    AccountingCostClassification,
    BenchmarkMode,
    DataAvailabilityState,
    PlantKpiMetrics,
)
from backend.app.services.ingestion.parser import IngestionParser
from backend.app.services.ingestion.models import IngestionTarget


class TestSourceWiseOpexSuite:
    """30 Comprehensive Unit Tests validating deterministic source-wise utility calculations."""

    # 1. Electricity: Grid energy + cost calculation
    def test_01_electricity_grid_calculation(self):
        breakdown = OpexCalculationEngine.calculate_electricity_source_breakdown(
            production_quantity=10000,
            total_electricity_kwh=Decimal("400000.00"),
            total_electricity_cost=Decimal("3000000.00"),
            grid_kwh=Decimal("400000.00"),
            grid_cost_inr=Decimal("3000000.00"),
        )
        assert breakdown.grid_kwh == Decimal("400000.00")
        assert breakdown.grid_cost_inr == Decimal("3000000.00")
        assert breakdown.purchased_kwh == Decimal("400000.00")

    # 2. Electricity: DG generation + cost calculation
    def test_02_electricity_dg_calculation(self):
        breakdown = OpexCalculationEngine.calculate_electricity_source_breakdown(
            production_quantity=10000,
            total_electricity_kwh=Decimal("450000.00"),
            total_electricity_cost=Decimal("3900000.00"),
            grid_kwh=Decimal("400000.00"),
            grid_cost_inr=Decimal("3000000.00"),
            dg_kwh=Decimal("50000.00"),
            dg_cost_inr=Decimal("900000.00"),
        )
        assert breakdown.dg_kwh == Decimal("50000.00")
        assert breakdown.dg_cost_inr == Decimal("900000.00")
        assert breakdown.total_generated_kwh == Decimal("50000.00")

    # 3. Electricity: Solar generation + cost calculation
    def test_03_electricity_solar_calculation(self):
        breakdown = OpexCalculationEngine.calculate_electricity_source_breakdown(
            production_quantity=10000,
            total_electricity_kwh=Decimal("480000.00"),
            total_electricity_cost=Decimal("3240000.00"),
            grid_kwh=Decimal("400000.00"),
            grid_cost_inr=Decimal("3000000.00"),
            solar_kwh=Decimal("80000.00"),
            solar_cost_inr=Decimal("240000.00"),
        )
        assert breakdown.solar_kwh == Decimal("80000.00")
        assert breakdown.solar_cost_inr == Decimal("240000.00")
        assert breakdown.total_generated_kwh == Decimal("80000.00")

    # 4. Electricity: Other captive generation calculation
    def test_04_electricity_other_captive_calculation(self):
        breakdown = OpexCalculationEngine.calculate_electricity_source_breakdown(
            production_quantity=10000,
            total_electricity_kwh=Decimal("420000.00"),
            total_electricity_cost=Decimal("3100000.00"),
            grid_kwh=Decimal("400000.00"),
            other_generated_kwh=Decimal("20000.00"),
            other_generation_cost_inr=Decimal("100000.00"),
        )
        assert breakdown.other_generated_kwh == Decimal("20000.00")
        assert breakdown.total_generated_kwh == Decimal("20000.00")

    # 5. Electricity: Total usable energy derivation = Purchased + Captive
    def test_05_electricity_total_usable_energy_sum(self):
        breakdown = OpexCalculationEngine.calculate_electricity_source_breakdown(
            production_quantity=10000,
            total_electricity_kwh=Decimal("0.0"),
            total_electricity_cost=Decimal("3900000.00"),
            grid_kwh=Decimal("400000.00"),
            dg_kwh=Decimal("20000.00"),
            solar_kwh=Decimal("30000.00"),
        )
        assert breakdown.total_energy_kwh == Decimal("450000.00")

    # 6. Electricity: Specific power derivation (kWh/veh)
    def test_06_electricity_specific_power(self):
        breakdown = OpexCalculationEngine.calculate_electricity_source_breakdown(
            production_quantity=20000,
            total_electricity_kwh=Decimal("800000.00"),
            total_electricity_cost=Decimal("6000000.00"),
            grid_kwh=Decimal("800000.00"),
        )
        assert breakdown.kwh_per_vehicle == Decimal("40.0000")

    # 7. Electricity: Blended cost per kWh calculation
    def test_07_electricity_cost_per_kwh(self):
        breakdown = OpexCalculationEngine.calculate_electricity_source_breakdown(
            production_quantity=10000,
            total_electricity_kwh=Decimal("500000.00"),
            total_electricity_cost=Decimal("3750000.00"),
        )
        assert breakdown.cost_per_kwh_inr == Decimal("7.5000")

    # 8. Electricity: Unit electricity cost per vehicle
    def test_08_electricity_cost_per_vehicle(self):
        breakdown = OpexCalculationEngine.calculate_electricity_source_breakdown(
            production_quantity=10000,
            total_electricity_kwh=Decimal("500000.00"),
            total_electricity_cost=Decimal("3750000.00"),
        )
        assert breakdown.cost_per_vehicle_inr == Decimal("375.0000")

    # 9. Water: Borewell water extraction + cost calculation
    def test_09_water_borewell_calculation(self):
        breakdown = OpexCalculationEngine.calculate_water_source_breakdown(
            production_quantity=10000,
            total_water_kl=Decimal("3000.00"),
            total_water_cost=Decimal("60000.00"),
            borewell_kl=Decimal("2000.00"),
            borewell_cost_inr=Decimal("30000.00"),
        )
        assert breakdown.borewell_kl == Decimal("2000.00")
        assert breakdown.borewell_cost_inr == Decimal("30000.00")

    # 10. Water: PWD / municipal water supply + cost calculation
    def test_10_water_pwd_calculation(self):
        breakdown = OpexCalculationEngine.calculate_water_source_breakdown(
            production_quantity=10000,
            total_water_kl=Decimal("3000.00"),
            total_water_cost=Decimal("90000.00"),
            pwd_kl=Decimal("3000.00"),
            pwd_cost_inr=Decimal("90000.00"),
        )
        assert breakdown.pwd_kl == Decimal("3000.00")
        assert breakdown.pwd_cost_inr == Decimal("90000.00")

    # 11. Water: Other water source calculation
    def test_11_water_other_source_calculation(self):
        breakdown = OpexCalculationEngine.calculate_water_source_breakdown(
            production_quantity=10000,
            total_water_kl=Decimal("1000.00"),
            total_water_cost=Decimal("50000.00"),
            other_water_kl=Decimal("1000.00"),
            other_water_cost_inr=Decimal("50000.00"),
        )
        assert breakdown.other_water_kl == Decimal("1000.00")

    # 12. Water: Total water volume aggregation (KL)
    def test_12_water_total_aggregation(self):
        breakdown = OpexCalculationEngine.calculate_water_source_breakdown(
            production_quantity=10000,
            total_water_kl=Decimal("0.0"),
            total_water_cost=Decimal("100000.00"),
            borewell_kl=Decimal("2500.00"),
            pwd_kl=Decimal("1500.00"),
        )
        assert breakdown.total_water_kl == Decimal("4000.00")

    # 13. Water: Specific water KPI (KL/veh)
    def test_13_water_kl_per_vehicle(self):
        breakdown = OpexCalculationEngine.calculate_water_source_breakdown(
            production_quantity=10000,
            total_water_kl=Decimal("3500.00"),
            total_water_cost=Decimal("87500.00"),
        )
        assert breakdown.kl_per_vehicle == Decimal("0.3500")

    # 14. Water: Cost per KL calculation
    def test_14_water_cost_per_kl(self):
        breakdown = OpexCalculationEngine.calculate_water_source_breakdown(
            production_quantity=10000,
            total_water_kl=Decimal("3500.00"),
            total_water_cost=Decimal("87500.00"),
        )
        assert breakdown.cost_per_kl_inr == Decimal("25.0000")

    # 15. Water: Unit water cost per vehicle
    def test_15_water_cost_per_vehicle(self):
        breakdown = OpexCalculationEngine.calculate_water_source_breakdown(
            production_quantity=10000,
            total_water_kl=Decimal("3500.00"),
            total_water_cost=Decimal("87500.00"),
        )
        assert breakdown.cost_per_vehicle_inr == Decimal("8.7500")

    # 16. Water: Zero-cost / unmetered water source handling without fabricating zeroes
    def test_16_water_unmetered_source_handling(self):
        breakdown = OpexCalculationEngine.calculate_water_source_breakdown(
            production_quantity=10000,
            total_water_kl=Decimal("3000.00"),
            total_water_cost=Decimal("0.0"),
            borewell_kl=Decimal("3000.00"),
            borewell_cost_inr=None,
        )
        assert breakdown.borewell_cost_inr is None
        assert breakdown.total_water_cost_inr == Decimal("0.0000")
        assert breakdown.cost_per_kl_inr == Decimal("0.0000")

    # 17. Compressed Air: Total air demand (CF)
    def test_17_compressed_air_total_demand(self):
        air = OpexCalculationEngine.calculate_compressed_air_breakdown(
            production_quantity=10000,
            compressed_air_cf_total=Decimal("34500.00"),
        )
        assert air.compressed_air_cf_total == Decimal("34500.00")

    # 18. Compressed Air: Specific demand (CF/veh)
    def test_18_compressed_air_specific_demand(self):
        air = OpexCalculationEngine.calculate_compressed_air_breakdown(
            production_quantity=10000,
            compressed_air_cf_total=Decimal("34500.00"),
        )
        assert air.compressed_air_cf_per_vehicle == Decimal("3.4500")

    # 19. Compressed Air: Compressor energy (kWh)
    def test_19_compressed_air_compressor_energy(self):
        air = OpexCalculationEngine.calculate_compressed_air_breakdown(
            production_quantity=10000,
            compressed_air_cf_total=Decimal("34500.00"),
            compressor_kwh_total=Decimal("741.75"),
        )
        assert air.compressor_kwh_total == Decimal("741.75")

    # 20. Compressed Air: Specific energy (kWh/CF)
    def test_20_compressed_air_specific_energy(self):
        air = OpexCalculationEngine.calculate_compressed_air_breakdown(
            production_quantity=10000,
            compressed_air_cf_total=Decimal("34500.00"),
            compressor_kwh_total=Decimal("741.75"),
        )
        assert air.compressor_kwh_per_cf == Decimal("0.021500")

    # 21. Compressed Air: Air generation yield (CF/kWh)
    def test_21_compressed_air_yield(self):
        air = OpexCalculationEngine.calculate_compressed_air_breakdown(
            production_quantity=10000,
            compressed_air_cf_total=Decimal("34500.00"),
            compressor_kwh_total=Decimal("741.75"),
        )
        assert air.compressor_cf_per_kwh == Decimal("46.5116")

    # 22. Compressed Air: Accounting classification (EMBEDDED_COST)
    def test_22_compressed_air_accounting_classification(self):
        air = OpexCalculationEngine.calculate_compressed_air_breakdown(
            production_quantity=10000,
            compressed_air_cf_total=Decimal("34500.00"),
            is_compressor_power_embedded=True,
        )
        assert air.accounting_classification == AccountingCostClassification.EMBEDDED_COST

    # 23. Natural Gas: Total gas volume (CF & Nm³)
    def test_23_natural_gas_total_volume(self):
        gas = OpexCalculationEngine.calculate_gas_fuel_breakdown(
            production_quantity=10000,
            gas_consumption_nm3=Decimal("12000.00"),
            gas_cost=Decimal("500000.00"),
            gas_cf_total=Decimal("423800.00"),
        )
        assert gas.gas_nm3_total == Decimal("12000.00")
        assert gas.gas_cf_total == Decimal("423800.00")

    # 24. Natural Gas: Specific gas consumption (CF/veh)
    def test_24_natural_gas_specific_consumption(self):
        gas = OpexCalculationEngine.calculate_gas_fuel_breakdown(
            production_quantity=10000,
            gas_consumption_nm3=Decimal("12000.00"),
            gas_cost=Decimal("500000.00"),
            gas_cf_total=Decimal("423800.00"),
        )
        assert gas.gas_cf_per_vehicle == Decimal("42.3800")
        assert gas.gas_nm3_per_vehicle == Decimal("1.2000")

    # 25. Natural Gas: Unit gas cost (₹/veh)
    def test_25_natural_gas_cost_per_vehicle(self):
        gas = OpexCalculationEngine.calculate_gas_fuel_breakdown(
            production_quantity=10000,
            gas_consumption_nm3=Decimal("12000.00"),
            gas_cost=Decimal("500000.00"),
            gas_cf_total=Decimal("423800.00"),
        )
        assert gas.gas_cost_per_vehicle_inr == Decimal("50.0000")

    # 26. Natural Gas: Volumetric gas tariff (₹/CF)
    def test_26_natural_gas_tariff_per_cf(self):
        gas = OpexCalculationEngine.calculate_gas_fuel_breakdown(
            production_quantity=10000,
            gas_consumption_nm3=Decimal("12000.00"),
            gas_cost=Decimal("500000.00"),
            gas_cf_total=Decimal("423800.00"),
        )
        assert gas.gas_cost_per_cf_inr == Decimal("1.1798")

    # 27. Accounting: Total plant OPEX double-counting safeguard
    def test_27_accounting_double_counting_protection(self):
        kpi = OpexCalculationEngine.calculate_plant_kpis(
            plant_id="plant-1",
            plant_code="PLANT_A",
            plant_name="Plant A",
            period_str="2024-04-01",
            production_quantity=10000,
            electricity_kwh=Decimal("400000.00"),
            electricity_cost=Decimal("3000000.00"),
            water_kl=Decimal("3000.00"),
            water_cost=Decimal("60000.00"),
            gas_consumption_nm3=Decimal("12000.00"),
            gas_cost=Decimal("500000.00"),
            compressed_air_nm3=Decimal("1000.00"),
            compressed_air_cost=Decimal("0.0"),  # Embedded in electricity
            waste_quantity_mt=Decimal("10.00"),
            waste_cost=Decimal("20000.00"),
            labor_cost=Decimal("1500000.00"),
            maintenance_cost=Decimal("600000.00"),
            other_opex=Decimal("270000.00"),
            total_opex=Decimal("5950000.00"),
            grid_kwh=Decimal("400000.00"),
            grid_cost_inr=Decimal("3000000.00"),
            compressed_air_cf_total=Decimal("34500.00"),
            compressor_kwh_total=Decimal("741.75"),
            is_compressor_power_embedded=True,
        )
        assert kpi.total_opex_per_vehicle == Decimal("595.0000")
        assert kpi.compressed_air.is_compressor_power_embedded is True
        assert kpi.compressed_air.accounting_classification == AccountingCostClassification.EMBEDDED_COST

    # 28. Ingestion: Column aliases for all source-wise utilities
    def test_28_ingestion_source_wise_aliases(self):
        headers = [
            "Plant", "Month", "Production_Vol",
            "Grid_Power_kWh", "Grid_Cost", "DG_Generation", "DG_Fuel_Cost",
            "Solar_Units", "Borewell_Water_KL", "Borewell_Cost", "Govt_Supply_KL",
            "Air_Volume_CF", "Compressor_Power_kWh", "Natural_Gas_CF", "Gas_Cost",
            "Labor_INR", "Maint_Cost", "Total_Plant_Cost"
        ]
        column_map = IngestionParser.match_columns_to_target(headers, IngestionTarget.PLANT_OPEX)
        assert column_map.get("grid_kwh") == "Grid_Power_kWh"
        assert column_map.get("grid_cost_inr") == "Grid_Cost"
        assert column_map.get("dg_kwh") == "DG_Generation"
        assert column_map.get("solar_kwh") == "Solar_Units"
        assert column_map.get("borewell_kl") == "Borewell_Water_KL"
        assert column_map.get("pwd_kl") == "Govt_Supply_KL"
        assert column_map.get("compressed_air_cf_total") == "Air_Volume_CF"
        assert column_map.get("compressor_kwh_total") == "Compressor_Power_kWh"
        assert column_map.get("gas_cf_total") == "Natural_Gas_CF"

    # 29. Benchmarking: Multi-factor comparability calculation across all 5 dimensions
    def test_29_benchmark_comparability_scoring(self):
        score = BenchmarkMethodology.calculate_comparability_score(
            target_scope="FULL_VEHICLE_ASSEMBLY",
            target_volume=200000,
            target_shifts=3,
            target_capacity=220000,
            target_tariff=Decimal("7.50"),
            peer_scope="FULL_VEHICLE_ASSEMBLY",
            peer_volume=180000,
            peer_shifts=3,
            peer_capacity=200000,
            peer_tariff=Decimal("7.20"),
            peer_total_opex_per_veh=Decimal("520.00"),
            candidate_plant_id="plant-dharuhera",
            candidate_plant_code="PLANT_B",
            candidate_plant_name="Dharuhera",
        )
        assert score.scope_similarity == Decimal("1.0000")
        assert score.volume_similarity == Decimal("0.9000")
        assert score.shift_similarity == Decimal("1.0000")
        assert score.comparability_index > Decimal("0.9000")

    # 30. Benchmarking: Variance decomposition and addressable opportunity
    def test_30_benchmark_variance_and_opportunity(self):
        variance = OpexCalculationEngine.decompose_variance(
            actual_total_opex_per_veh=Decimal("595.00"),
            benchmark_total_opex_per_veh=Decimal("520.00"),
            actual_grid_tariff=Decimal("7.50"),
            benchmark_grid_tariff=Decimal("7.20"),
            benchmark_kwh_per_veh=Decimal("40.00"),
            actual_capacity_util=Decimal("0.90"),
            benchmark_capacity_util=Decimal("0.90"),
        )
        assert variance.total_gap_per_vehicle == Decimal("75.0000")
        assert variance.tariff_variance_per_vehicle == Decimal("12.0000")
        assert variance.addressable_gap_per_vehicle == Decimal("63.0000")
        
        opp_inr, opp_cr = OpexCalculationEngine.calculate_annual_opportunity(
            addressable_gap_per_vehicle=variance.addressable_gap_per_vehicle,
            annual_production_volume=2400000,
        )
        assert opp_inr == Decimal("151200000.00")
        assert opp_cr == Decimal("15.1200")
