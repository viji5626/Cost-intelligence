"""
Unit Tests for Plant Master, Production Records, OPEX, and Benchmark Models
"""

from database.models.plant_opex import (
    Plant,
    ProductionRecord,
    OpexRecord,
    BenchmarkRecord,
)


def test_plant_master_instantiation():
    plant = Plant(
        id="plt-haridwar",
        plant_code="PLANT-HARIDWAR",
        name="Haridwar Plant",
        location="Haridwar",
        state="Uttarakhand",
        country="India",
        annual_capacity_vehicles=2700000,
        operating_days_per_year=300,
        shifts_per_day=3,
        grid_tariff_inr_kwh=6.85,
    )
    assert plant.name == "Haridwar Plant"
    assert plant.annual_capacity_vehicles == 2700000
    assert plant.grid_tariff_inr_kwh == 6.85


def test_opex_and_benchmark_models():
    opex = OpexRecord(
        id="opx-01",
        plant_id="plt-haridwar",
        period="2024-04-01",
        production_quantity=185000,
        electricity_kwh=4255000.0,
        electricity_cost=29146750.0,
        water_kl=45000.0,
        water_cost=1575000.0,
        gas_consumption_nm3=120000.0,
        gas_cost=5400000.0,
        compressed_air_nm3=2500000.0,
        compressed_air_cost=3750000.0,
        waste_quantity_mt=45.0,
        waste_cost=225000.0,
        labor_cost=45000000.0,
        maintenance_cost=12500000.0,
        other_opex=4500000.0,
        total_opex=102096750.0,
        currency="INR",
        source_system="SAP_CO_PLANT",
        is_anomaly=False,
    )

    bm = BenchmarkRecord(
        id="bm-01",
        benchmark_code="BM-HAR-2024",
        benchmark_name="Haridwar 2024 Target Baseline",
        benchmark_type="BEST_COMPARABLE",
        plant_id="plt-haridwar",
        period="2024-04-01",
        kwh_per_vehicle=21.5,
        kl_per_vehicle=0.22,
        opex_per_vehicle=515.0,
        comparability_index=0.95,
    )

    assert opex.production_quantity == 185000
    assert opex.total_opex == 102096750.0
    assert bm.benchmark_type == "BEST_COMPARABLE"
    assert bm.comparability_index == 0.95
