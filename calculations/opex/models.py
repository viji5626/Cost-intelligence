"""
Plant OPEX and Benchmark Methodology Calculation Models
Source-wise utility accounting and deterministic financial KPI representations.
"""

from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BenchmarkMode(str, Enum):
    BEST_COMPARABLE = "BEST_COMPARABLE"      # Selects peer with highest comparability score & superior efficiency
    PEER_GROUP = "PEER_GROUP"                # Top quartile / group weighted average
    HISTORICAL_BASELINE = "HISTORICAL_BASELINE"  # Plant's best historical performance
    MANAGEMENT_TARGET = "MANAGEMENT_TARGET"  # Corporate strategic target


class AccountingCostClassification(str, Enum):
    """Rigorous financial accounting classification preventing double-counting."""
    PRIMARY_FINANCIAL_COST = "PRIMARY_FINANCIAL_COST"  # Primary balance-sheet OPEX line item
    DERIVED_UTILITY_METRIC = "DERIVED_UTILITY_METRIC"  # Physical engineering/efficiency metric (kWh, CF, KL)
    ALLOCATED_COST = "ALLOCATED_COST"                  # Separately billed utility allocation
    EMBEDDED_COST = "EMBEDDED_COST"                    # Utility cost embedded in parent utility line (e.g. compressor in power)
    NOT_AVAILABLE = "NOT_AVAILABLE"                    # Cost unmetered or not separately provided


class DataAvailabilityState(str, Enum):
    """Explicit data presence state ensuring no zero fabrication for missing data."""
    AVAILABLE = "AVAILABLE"
    DERIVED = "DERIVED"
    MISSING = "MISSING"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ElectricitySourceBreakdown(BaseModel):
    """Source-wise electricity consumption, captive generation, and cost metrics."""
    grid_kwh: Optional[Decimal] = None
    grid_cost_inr: Optional[Decimal] = None
    dg_kwh: Optional[Decimal] = None
    dg_cost_inr: Optional[Decimal] = None
    solar_kwh: Optional[Decimal] = None
    solar_cost_inr: Optional[Decimal] = None
    other_generated_kwh: Optional[Decimal] = None
    other_generation_cost_inr: Optional[Decimal] = None
    
    # Derivations & Totals
    purchased_kwh: Optional[Decimal] = None
    total_generated_kwh: Optional[Decimal] = None
    total_energy_kwh: Decimal
    total_electricity_cost_inr: Decimal
    kwh_per_vehicle: Decimal
    cost_per_kwh_inr: Optional[Decimal] = None
    cost_per_vehicle_inr: Decimal
    
    availability: DataAvailabilityState = DataAvailabilityState.AVAILABLE
    accounting_classification: AccountingCostClassification = AccountingCostClassification.PRIMARY_FINANCIAL_COST


class WaterSourceBreakdown(BaseModel):
    """Source-wise water extraction, municipal supply, and cost metrics."""
    borewell_kl: Optional[Decimal] = None
    borewell_cost_inr: Optional[Decimal] = None
    pwd_kl: Optional[Decimal] = None
    pwd_cost_inr: Optional[Decimal] = None
    other_water_kl: Optional[Decimal] = None
    other_water_cost_inr: Optional[Decimal] = None
    
    # Totals & Normalized KPIs
    total_water_kl: Decimal
    total_water_cost_inr: Decimal
    kl_per_vehicle: Decimal
    cost_per_kl_inr: Optional[Decimal] = None
    cost_per_vehicle_inr: Decimal
    
    availability: DataAvailabilityState = DataAvailabilityState.AVAILABLE


class CompressedAirBreakdown(BaseModel):
    """Compressed air physical demand, compressor energy, and generation efficiency."""
    compressed_air_cf_total: Optional[Decimal] = None
    compressed_air_cf_per_vehicle: Optional[Decimal] = None
    compressor_kwh_total: Optional[Decimal] = None
    compressor_kwh_per_cf: Optional[Decimal] = None
    compressor_cf_per_kwh: Optional[Decimal] = None
    compressed_air_cost_inr: Optional[Decimal] = None
    compressed_air_cost_per_cf_inr: Optional[Decimal] = None
    compressed_air_cost_per_vehicle_inr: Optional[Decimal] = None
    
    is_compressor_power_embedded: bool = True
    availability: DataAvailabilityState = DataAvailabilityState.AVAILABLE
    accounting_classification: AccountingCostClassification = AccountingCostClassification.EMBEDDED_COST


class GasFuelBreakdown(BaseModel):
    """Natural gas / Fuel consumption, source classification, and unit cost."""
    gas_cf_total: Optional[Decimal] = None
    gas_nm3_total: Optional[Decimal] = None
    gas_cf_per_vehicle: Optional[Decimal] = None
    gas_nm3_per_vehicle: Optional[Decimal] = None
    gas_cost_inr: Decimal
    gas_cost_per_cf_inr: Optional[Decimal] = None
    gas_cost_per_vehicle_inr: Decimal
    gas_source_type: str = "PNG"
    
    availability: DataAvailabilityState = DataAvailabilityState.AVAILABLE


class PlantKpiMetrics(BaseModel):
    """Calculated normalized operational KPIs per vehicle produced with full source-wise utility breakdowns."""

    plant_id: str
    plant_code: str
    plant_name: str
    period: str
    production_quantity: int

    # Energy & Utilities Primary KPIs (per vehicle)
    kwh_per_vehicle: Decimal
    electricity_inr_per_vehicle: Decimal
    water_kl_per_vehicle: Decimal
    water_inr_per_vehicle: Decimal
    gas_cf_per_vehicle: Optional[Decimal] = None
    gas_nm3_per_vehicle: Decimal
    gas_inr_per_vehicle: Decimal
    compressed_air_cf_per_vehicle: Optional[Decimal] = None
    compressed_air_nm3_per_vehicle: Decimal
    compressed_air_inr_per_vehicle: Decimal
    compressed_air_cf_total: Optional[Decimal] = None
    compressor_kwh_total: Optional[Decimal] = None
    compressor_kwh_per_cf: Optional[Decimal] = None
    compressor_cf_per_kwh: Optional[Decimal] = None
    compressed_air_cost_inr: Optional[Decimal] = None
    is_compressor_power_embedded: bool = True

    # Extended Source-Wise Utility Breakdown Domains
    electricity: Optional[ElectricitySourceBreakdown] = None
    water: Optional[WaterSourceBreakdown] = None
    compressed_air: Optional[CompressedAirBreakdown] = None
    gas_fuel: Optional[GasFuelBreakdown] = None

    # Maintenance, Labor & Operations KPIs (per vehicle)
    waste_inr_per_vehicle: Decimal
    labor_inr_per_vehicle: Decimal
    maintenance_inr_per_vehicle: Decimal
    other_inr_per_vehicle: Decimal
    total_opex_per_vehicle: Decimal

    # Gross totals (Rupees)
    gross_total_opex: Decimal
    currency: str = "INR"
    is_anomaly: bool = False


class ComparabilityWeights(BaseModel):
    """Configurable weights for multi-factor plant comparability index (Sum = 1.0)."""

    scope_weight: Decimal = Decimal("0.35")       # Manufacturing scope (Casting, Machining, Paint, Assembly)
    volume_weight: Decimal = Decimal("0.25")      # Production volume / scale similarity
    shift_weight: Decimal = Decimal("0.15")       # Operating days and shift patterns
    capacity_weight: Decimal = Decimal("0.15")    # Capacity utilization rate
    tariff_weight: Decimal = Decimal("0.10")      # Power tariff comparability


class PlantComparabilityScore(BaseModel):
    """Evaluated comparability score between target plant and a candidate benchmark peer."""

    candidate_plant_id: str
    candidate_plant_code: str
    candidate_plant_name: str
    comparability_index: Decimal  # 0.0 to 1.0 (Higher = more comparable)
    scope_similarity: Decimal
    volume_similarity: Decimal
    shift_similarity: Decimal
    capacity_similarity: Decimal
    tariff_similarity: Decimal
    total_opex_per_vehicle: Decimal


class VarianceDecomposition(BaseModel):
    """Deterministic separation of total OPEX gap into controllable and external driver variances."""

    total_gap_per_vehicle: Decimal             # Actual ₹/veh - Benchmark ₹/veh
    tariff_variance_per_vehicle: Decimal       # External regional power tariff differential
    volume_variance_per_vehicle: Decimal       # Fixed overhead absorption differential
    addressable_gap_per_vehicle: Decimal       # Pure operational efficiency gap (Controllable)
    efficiency_gap_percentage: Decimal         # Percentage of total gap that is addressable


class BenchmarkOpportunityResult(BaseModel):
    """Full deterministic multi-factor benchmark gap analysis and financial opportunity report."""

    target_plant_id: str
    target_plant_name: str
    target_period: str
    target_actual_kpi: PlantKpiMetrics

    benchmark_mode: BenchmarkMode
    benchmark_source_name: str
    benchmark_comparability_index: Decimal

    # Target Benchmark Values (per vehicle)
    benchmark_kwh_per_vehicle: Decimal
    benchmark_water_kl_per_vehicle: Decimal
    benchmark_gas_cf_per_vehicle: Optional[Decimal] = None
    benchmark_total_opex_per_vehicle: Decimal

    # Benchmark Utility Dimensions
    benchmark_compressed_air_cf_per_vehicle: Optional[Decimal] = None
    benchmark_compressor_kwh_per_cf: Optional[Decimal] = None
    benchmark_compressor_cf_per_kwh: Optional[Decimal] = None
    benchmark_compressed_air_cost_per_vehicle: Optional[Decimal] = None

    # Benchmark Utility Breakdown Snapshots
    benchmark_electricity: Optional[ElectricitySourceBreakdown] = None
    benchmark_water: Optional[WaterSourceBreakdown] = None
    benchmark_compressed_air: Optional[CompressedAirBreakdown] = None
    benchmark_gas_fuel: Optional[GasFuelBreakdown] = None

    # Variance and Financial Opportunities
    variance: VarianceDecomposition
    annual_production_volume: int
    gross_annual_opportunity_inr: Decimal      # Addressable Gap * Annual Volume
    gross_annual_opportunity_crores: Decimal   # In Crore Rupees (₹ Cr)
    
    # Audit & Provenance Metadata
    calculation_id: str
    calculation_timestamp: str
    calculation_hash: str
    provenance_details: Dict[str, Any] = Field(default_factory=dict)
