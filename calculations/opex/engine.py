"""
Deterministic Plant OPEX Calculation Engine
Zero LLM arithmetic: pure Python Decimal calculations for financial and operational KPIs.
Includes source-wise utility derivations (Electricity, Water, Compressed Air, Gas)
and strict double-counting protection rules.
"""

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Optional, Tuple

from calculations.opex.models import (
    AccountingCostClassification,
    CompressedAirBreakdown,
    DataAvailabilityState,
    ElectricitySourceBreakdown,
    GasFuelBreakdown,
    PlantKpiMetrics,
    VarianceDecomposition,
    WaterSourceBreakdown,
)


class OpexCalculationEngine:
    """Pure mathematical calculation engine for Plant OPEX KPIs and variance analysis."""

    @staticmethod
    def _round(value: Decimal, places: int = 4) -> Decimal:
        """Standardized commercial half-up rounding for deterministic financial figures."""
        q = Decimal("10") ** -places
        return value.quantize(q, rounding=ROUND_HALF_UP)

    @classmethod
    def calculate_electricity_source_breakdown(
        cls,
        production_quantity: int,
        total_electricity_kwh: Decimal,
        total_electricity_cost: Decimal,
        grid_kwh: Optional[Decimal] = None,
        grid_cost_inr: Optional[Decimal] = None,
        dg_kwh: Optional[Decimal] = None,
        dg_cost_inr: Optional[Decimal] = None,
        solar_kwh: Optional[Decimal] = None,
        solar_cost_inr: Optional[Decimal] = None,
        other_generated_kwh: Optional[Decimal] = None,
        other_generation_cost_inr: Optional[Decimal] = None,
    ) -> ElectricitySourceBreakdown:
        """
        Calculates deterministic source-wise electricity metrics:
        - Purchased energy: Grid
        - Captive generation: DG + Solar + Other (without double-counting)
        - Total usable energy
        - Specific power (kWh/veh) and cost per kWh
        """
        prod_dec = Decimal(str(production_quantity)) if production_quantity > 0 else Decimal("1")
        
        # 1. Purchased & Captive Generation Summation
        purchased_kwh = grid_kwh
        captive_sources = [s for s in [dg_kwh, solar_kwh, other_generated_kwh] if s is not None]
        total_generated_kwh = sum(captive_sources, Decimal("0.0")) if captive_sources else None

        # 2. Total Energy Derivation
        if grid_kwh is not None or total_generated_kwh is not None:
            calc_energy = (grid_kwh or Decimal("0.0")) + (total_generated_kwh or Decimal("0.0"))
            total_energy = calc_energy if calc_energy > Decimal("0.0") else total_electricity_kwh
        else:
            total_energy = total_electricity_kwh

        # 3. Specific Metrics
        kwh_per_veh = cls._round(total_energy / prod_dec, 4) if production_quantity > 0 else Decimal("0.0")
        cost_per_veh = cls._round(total_electricity_cost / prod_dec, 4) if production_quantity > 0 else Decimal("0.0")
        cost_per_kwh = cls._round(total_electricity_cost / total_energy, 4) if total_energy > Decimal("0.0") else None

        has_source_data = any(s is not None for s in [grid_kwh, dg_kwh, solar_kwh, other_generated_kwh])
        availability = DataAvailabilityState.AVAILABLE if has_source_data else DataAvailabilityState.DERIVED

        return ElectricitySourceBreakdown(
            grid_kwh=grid_kwh,
            grid_cost_inr=grid_cost_inr,
            dg_kwh=dg_kwh,
            dg_cost_inr=dg_cost_inr,
            solar_kwh=solar_kwh,
            solar_cost_inr=solar_cost_inr,
            other_generated_kwh=other_generated_kwh,
            other_generation_cost_inr=other_generation_cost_inr,
            purchased_kwh=purchased_kwh,
            total_generated_kwh=total_generated_kwh,
            total_energy_kwh=cls._round(total_energy, 4),
            total_electricity_cost_inr=cls._round(total_electricity_cost, 4),
            kwh_per_vehicle=kwh_per_veh,
            cost_per_kwh_inr=cost_per_kwh,
            cost_per_vehicle_inr=cost_per_veh,
            availability=availability,
            accounting_classification=AccountingCostClassification.PRIMARY_FINANCIAL_COST,
        )

    @classmethod
    def calculate_water_source_breakdown(
        cls,
        production_quantity: int,
        total_water_kl: Decimal,
        total_water_cost: Decimal,
        borewell_kl: Optional[Decimal] = None,
        borewell_cost_inr: Optional[Decimal] = None,
        pwd_kl: Optional[Decimal] = None,
        pwd_cost_inr: Optional[Decimal] = None,
        other_water_kl: Optional[Decimal] = None,
        other_water_cost_inr: Optional[Decimal] = None,
    ) -> WaterSourceBreakdown:
        """Calculates deterministic source-wise water metrics (Borewell, PWD, Municipal, Other)."""
        prod_dec = Decimal(str(production_quantity)) if production_quantity > 0 else Decimal("1")
        
        water_sources = [w for w in [borewell_kl, pwd_kl, other_water_kl] if w is not None]
        if water_sources:
            calc_water = sum(water_sources, Decimal("0.0"))
            effective_total_kl = calc_water if calc_water > Decimal("0.0") else total_water_kl
        else:
            effective_total_kl = total_water_kl

        kl_per_veh = cls._round(effective_total_kl / prod_dec, 4) if production_quantity > 0 else Decimal("0.0")
        cost_per_veh = cls._round(total_water_cost / prod_dec, 4) if production_quantity > 0 else Decimal("0.0")
        cost_per_kl = cls._round(total_water_cost / effective_total_kl, 4) if effective_total_kl > Decimal("0.0") else None

        has_source_data = any(s is not None for s in [borewell_kl, pwd_kl, other_water_kl])
        availability = DataAvailabilityState.AVAILABLE if has_source_data else DataAvailabilityState.DERIVED

        return WaterSourceBreakdown(
            borewell_kl=borewell_kl,
            borewell_cost_inr=borewell_cost_inr,
            pwd_kl=pwd_kl,
            pwd_cost_inr=pwd_cost_inr,
            other_water_kl=other_water_kl,
            other_water_cost_inr=other_water_cost_inr,
            total_water_kl=cls._round(effective_total_kl, 4),
            total_water_cost_inr=cls._round(total_water_cost, 4),
            kl_per_vehicle=kl_per_veh,
            cost_per_kl_inr=cost_per_kl,
            cost_per_vehicle_inr=cost_per_veh,
            availability=availability,
        )

    @classmethod
    def calculate_compressed_air_breakdown(
        cls,
        production_quantity: int,
        compressed_air_cf_total: Optional[Decimal] = None,
        compressor_kwh_total: Optional[Decimal] = None,
        compressed_air_cost_inr: Optional[Decimal] = None,
        is_compressor_power_embedded: bool = True,
    ) -> CompressedAirBreakdown:
        """Calculates deterministic compressed air demand and generation efficiency metrics."""
        prod_dec = Decimal(str(production_quantity)) if production_quantity > 0 else Decimal("1")
        
        cf_per_veh: Optional[Decimal] = None
        kwh_per_cf: Optional[Decimal] = None
        cf_per_kwh: Optional[Decimal] = None
        cost_per_cf: Optional[Decimal] = None
        cost_per_veh: Optional[Decimal] = None

        if production_quantity > 0:
            if compressed_air_cf_total is not None and compressed_air_cf_total >= Decimal("0.0"):
                cf_per_veh = cls._round(compressed_air_cf_total / prod_dec, 4)
            if compressed_air_cost_inr is not None and compressed_air_cost_inr >= Decimal("0.0"):
                cost_per_veh = cls._round(compressed_air_cost_inr / prod_dec, 4)

        if (
            compressed_air_cf_total is not None
            and compressor_kwh_total is not None
            and compressed_air_cf_total > Decimal("0.0")
            and compressor_kwh_total >= Decimal("0.0")
        ):
            kwh_per_cf = cls._round(compressor_kwh_total / compressed_air_cf_total, 6)

        if (
            compressed_air_cf_total is not None
            and compressor_kwh_total is not None
            and compressor_kwh_total > Decimal("0.0")
            and compressed_air_cf_total >= Decimal("0.0")
        ):
            cf_per_kwh = cls._round(compressed_air_cf_total / compressor_kwh_total, 4)

        if (
            compressed_air_cost_inr is not None
            and compressed_air_cf_total is not None
            and compressed_air_cf_total > Decimal("0.0")
        ):
            cost_per_cf = cls._round(compressed_air_cost_inr / compressed_air_cf_total, 4)

        availability = DataAvailabilityState.AVAILABLE if compressed_air_cf_total is not None else DataAvailabilityState.MISSING
        classification = (
            AccountingCostClassification.EMBEDDED_COST
            if is_compressor_power_embedded
            else AccountingCostClassification.ALLOCATED_COST
        )

        return CompressedAirBreakdown(
            compressed_air_cf_total=compressed_air_cf_total,
            compressed_air_cf_per_vehicle=cf_per_veh,
            compressor_kwh_total=compressor_kwh_total,
            compressor_kwh_per_cf=kwh_per_cf,
            compressor_cf_per_kwh=cf_per_kwh,
            compressed_air_cost_inr=compressed_air_cost_inr,
            compressed_air_cost_per_cf_inr=cost_per_cf,
            compressed_air_cost_per_vehicle_inr=cost_per_veh,
            is_compressor_power_embedded=is_compressor_power_embedded,
            availability=availability,
            accounting_classification=classification,
        )

    @classmethod
    def calculate_compressed_air_metrics(
        cls,
        production_quantity: int,
        compressed_air_cf_total: Optional[Decimal] = None,
        compressor_kwh_total: Optional[Decimal] = None,
        compressed_air_cost_inr: Optional[Decimal] = None,
    ) -> Tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """Backwards-compatible helper returning (cf_per_veh, kwh_per_cf, cf_per_kwh, cost_per_veh)."""
        air = cls.calculate_compressed_air_breakdown(
            production_quantity=production_quantity,
            compressed_air_cf_total=compressed_air_cf_total,
            compressor_kwh_total=compressor_kwh_total,
            compressed_air_cost_inr=compressed_air_cost_inr,
        )
        return (
            air.compressed_air_cf_per_vehicle,
            air.compressor_kwh_per_cf,
            air.compressor_cf_per_kwh,
            air.compressed_air_cost_per_vehicle_inr,
        )

    @classmethod
    def calculate_gas_fuel_breakdown(
        cls,
        production_quantity: int,
        gas_consumption_nm3: Decimal,
        gas_cost: Decimal,
        gas_cf_total: Optional[Decimal] = None,
        gas_source_type: str = "PNG",
    ) -> GasFuelBreakdown:
        """Calculates natural gas / fuel consumption and unit costs."""
        prod_dec = Decimal(str(production_quantity)) if production_quantity > 0 else Decimal("1")
        
        gas_cf_per_veh = cls._round(gas_cf_total / prod_dec, 4) if gas_cf_total is not None and production_quantity > 0 else None
        gas_nm3_per_veh = cls._round(gas_consumption_nm3 / prod_dec, 4) if production_quantity > 0 else Decimal("0.0")
        gas_cost_per_veh = cls._round(gas_cost / prod_dec, 4) if production_quantity > 0 else Decimal("0.0")
        gas_cost_per_cf = cls._round(gas_cost / gas_cf_total, 4) if gas_cf_total is not None and gas_cf_total > Decimal("0.0") else None

        availability = DataAvailabilityState.AVAILABLE if (gas_cf_total is not None or gas_consumption_nm3 > Decimal("0.0")) else DataAvailabilityState.MISSING

        return GasFuelBreakdown(
            gas_cf_total=gas_cf_total,
            gas_nm3_total=cls._round(gas_consumption_nm3, 4),
            gas_cf_per_vehicle=gas_cf_per_veh,
            gas_nm3_per_vehicle=gas_nm3_per_veh,
            gas_cost_inr=cls._round(gas_cost, 4),
            gas_cost_per_cf_inr=gas_cost_per_cf,
            gas_cost_per_vehicle_inr=gas_cost_per_veh,
            gas_source_type=gas_source_type,
            availability=availability,
        )

    @classmethod
    def calculate_plant_kpis(
        cls,
        plant_id: str,
        plant_code: str,
        plant_name: str,
        period_str: str,
        production_quantity: int,
        electricity_kwh: Decimal,
        electricity_cost: Decimal,
        water_kl: Decimal,
        water_cost: Decimal,
        gas_consumption_nm3: Decimal,
        gas_cost: Decimal,
        compressed_air_nm3: Decimal,
        compressed_air_cost: Decimal,
        waste_quantity_mt: Decimal,
        waste_cost: Decimal,
        labor_cost: Decimal,
        maintenance_cost: Decimal,
        other_opex: Decimal,
        total_opex: Decimal,
        grid_kwh: Optional[Decimal] = None,
        grid_cost_inr: Optional[Decimal] = None,
        dg_kwh: Optional[Decimal] = None,
        dg_cost_inr: Optional[Decimal] = None,
        solar_kwh: Optional[Decimal] = None,
        solar_cost_inr: Optional[Decimal] = None,
        other_generated_kwh: Optional[Decimal] = None,
        other_generation_cost_inr: Optional[Decimal] = None,
        borewell_kl: Optional[Decimal] = None,
        borewell_cost_inr: Optional[Decimal] = None,
        pwd_kl: Optional[Decimal] = None,
        pwd_cost_inr: Optional[Decimal] = None,
        other_water_kl: Optional[Decimal] = None,
        other_water_cost_inr: Optional[Decimal] = None,
        compressed_air_cf_total: Optional[Decimal] = None,
        compressor_kwh_total: Optional[Decimal] = None,
        compressed_air_cost_inr: Optional[Decimal] = None,
        is_compressor_power_embedded: bool = True,
        gas_cf_total: Optional[Decimal] = None,
        gas_source_type: str = "PNG",
        is_anomaly: bool = False,
    ) -> PlantKpiMetrics:
        """Calculates normalized operational KPIs per vehicle produced with full source-wise utility breakdowns."""
        if production_quantity <= 0:
            raise ValueError(f"Cannot normalize OPEX KPIs: production_quantity={production_quantity} must be > 0.")

        prod_dec = Decimal(str(production_quantity))

        # 1. Source-Wise Sub-Domain Calculations
        elec_breakdown = cls.calculate_electricity_source_breakdown(
            production_quantity=production_quantity,
            total_electricity_kwh=electricity_kwh,
            total_electricity_cost=electricity_cost,
            grid_kwh=grid_kwh,
            grid_cost_inr=grid_cost_inr,
            dg_kwh=dg_kwh,
            dg_cost_inr=dg_cost_inr,
            solar_kwh=solar_kwh,
            solar_cost_inr=solar_cost_inr,
            other_generated_kwh=other_generated_kwh,
            other_generation_cost_inr=other_generation_cost_inr,
        )

        water_breakdown = cls.calculate_water_source_breakdown(
            production_quantity=production_quantity,
            total_water_kl=water_kl,
            total_water_cost=water_cost,
            borewell_kl=borewell_kl,
            borewell_cost_inr=borewell_cost_inr,
            pwd_kl=pwd_kl,
            pwd_cost_inr=pwd_cost_inr,
            other_water_kl=other_water_kl,
            other_water_cost_inr=other_water_cost_inr,
        )

        air_breakdown = cls.calculate_compressed_air_breakdown(
            production_quantity=production_quantity,
            compressed_air_cf_total=compressed_air_cf_total,
            compressor_kwh_total=compressor_kwh_total,
            compressed_air_cost_inr=compressed_air_cost_inr if compressed_air_cost_inr is not None else (compressed_air_cost if compressed_air_cost > Decimal("0.0") else None),
            is_compressor_power_embedded=is_compressor_power_embedded,
        )

        gas_breakdown = cls.calculate_gas_fuel_breakdown(
            production_quantity=production_quantity,
            gas_consumption_nm3=gas_consumption_nm3,
            gas_cost=gas_cost,
            gas_cf_total=gas_cf_total,
            gas_source_type=gas_source_type,
        )

        # 2. Operations & Maintenance
        waste_inr_per_veh = cls._round(waste_cost / prod_dec, 4)
        labor_inr_per_veh = cls._round(labor_cost / prod_dec, 4)
        maint_inr_per_veh = cls._round(maintenance_cost / prod_dec, 4)
        other_inr_per_veh = cls._round(other_opex / prod_dec, 4)
        total_opex_per_veh = cls._round(total_opex / prod_dec, 4)

        return PlantKpiMetrics(
            plant_id=plant_id,
            plant_code=plant_code,
            plant_name=plant_name,
            period=period_str,
            production_quantity=production_quantity,
            kwh_per_vehicle=elec_breakdown.kwh_per_vehicle,
            electricity_inr_per_vehicle=elec_breakdown.cost_per_vehicle_inr,
            water_kl_per_vehicle=water_breakdown.kl_per_vehicle,
            water_inr_per_vehicle=water_breakdown.cost_per_vehicle_inr,
            gas_cf_per_vehicle=gas_breakdown.gas_cf_per_vehicle,
            gas_nm3_per_vehicle=gas_breakdown.gas_nm3_per_vehicle,
            gas_inr_per_vehicle=gas_breakdown.gas_cost_per_vehicle_inr,
            compressed_air_cf_per_vehicle=air_breakdown.compressed_air_cf_per_vehicle,
            compressed_air_nm3_per_vehicle=cls._round(compressed_air_nm3 / prod_dec, 4),
            compressed_air_inr_per_vehicle=cls._round(compressed_air_cost / prod_dec, 4),
            compressed_air_cf_total=air_breakdown.compressed_air_cf_total,
            compressor_kwh_total=air_breakdown.compressor_kwh_total,
            compressor_kwh_per_cf=air_breakdown.compressor_kwh_per_cf,
            compressor_cf_per_kwh=air_breakdown.compressor_cf_per_kwh,
            compressed_air_cost_inr=air_breakdown.compressed_air_cost_inr,
            is_compressor_power_embedded=is_compressor_power_embedded,
            electricity=elec_breakdown,
            water=water_breakdown,
            compressed_air=air_breakdown,
            gas_fuel=gas_breakdown,
            waste_inr_per_vehicle=waste_inr_per_veh,
            labor_inr_per_vehicle=labor_inr_per_veh,
            maintenance_inr_per_vehicle=maint_inr_per_veh,
            other_inr_per_vehicle=other_inr_per_veh,
            total_opex_per_vehicle=total_opex_per_veh,
            gross_total_opex=cls._round(total_opex, 2),
            currency="INR",
            is_anomaly=is_anomaly,
        )

    @classmethod
    def decompose_variance(
        cls,
        actual_total_opex_per_veh: Decimal,
        benchmark_total_opex_per_veh: Decimal,
        actual_grid_tariff: Optional[Decimal],
        benchmark_grid_tariff: Optional[Decimal],
        benchmark_kwh_per_veh: Decimal,
        actual_capacity_util: Decimal,
        benchmark_capacity_util: Decimal,
        fixed_overhead_ratio: Decimal = Decimal("0.30"),
    ) -> VarianceDecomposition:
        """Decomposes the total gap into Tariff Variance, Volume/Utilization Variance, and Addressable Operational Efficiency Gap."""
        total_gap = cls._round(actual_total_opex_per_veh - benchmark_total_opex_per_veh, 4)

        # 1. Tariff Variance = (Actual Tariff - Benchmark Tariff) * Benchmark kWh/veh
        tariff_variance = Decimal("0.0")
        if actual_grid_tariff is not None and benchmark_grid_tariff is not None:
            tariff_diff = actual_grid_tariff - benchmark_grid_tariff
            tariff_variance = cls._round(tariff_diff * benchmark_kwh_per_veh, 4)

        # 2. Volume/Utilization Absorption Variance
        vol_variance = Decimal("0.0")
        if benchmark_capacity_util > Decimal("0.0") and actual_capacity_util > Decimal("0.0"):
            util_ratio = (benchmark_capacity_util - actual_capacity_util) / benchmark_capacity_util
            raw_vol = benchmark_total_opex_per_veh * fixed_overhead_ratio * util_ratio
            vol_variance = cls._round(max(Decimal("-100.0"), min(raw_vol, Decimal("150.0"))), 4)

        # 3. Addressable Operational Efficiency Gap (Controllable)
        raw_addressable = total_gap - tariff_variance - vol_variance
        addressable_gap = cls._round(max(Decimal("0.0"), raw_addressable), 4)

        efficiency_pct = Decimal("0.0")
        if total_gap > Decimal("0.0"):
            efficiency_pct = cls._round((addressable_gap / total_gap) * Decimal("100.0"), 2)

        return VarianceDecomposition(
            total_gap_per_vehicle=total_gap,
            tariff_variance_per_vehicle=tariff_variance,
            volume_variance_per_vehicle=vol_variance,
            addressable_gap_per_vehicle=addressable_gap,
            efficiency_gap_percentage=efficiency_pct,
        )

    @classmethod
    def calculate_annual_opportunity(
        cls,
        addressable_gap_per_vehicle: Decimal,
        annual_production_volume: int,
    ) -> Tuple[Decimal, Decimal]:
        """Calculates gross annual opportunity: Returns (Opportunity in Rupees, Opportunity in Crore Rupees [₹ Cr])."""
        vol_dec = Decimal(str(annual_production_volume))
        opp_inr = cls._round(addressable_gap_per_vehicle * vol_dec, 2)
        opp_cr = cls._round(opp_inr / Decimal("10000000"), 4)
        return opp_inr, opp_cr

    @classmethod
    def generate_calculation_provenance(
        cls,
        calculation_id: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        timestamp_str: Optional[str] = None,
    ) -> Tuple[str, str]:
        """Generates calculation timestamp and SHA-256 cryptographic provenance hash."""
        ts = timestamp_str or datetime.now(timezone.utc).isoformat()
        payload = {
            "calc_id": calculation_id,
            "timestamp": ts,
            "inputs": {k: str(v) for k, v in inputs.items()},
            "outputs": {k: str(v) for k, v in outputs.items()},
        }
        raw_json = json.dumps(payload, sort_keys=True)
        calc_hash = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
        return ts, calc_hash
