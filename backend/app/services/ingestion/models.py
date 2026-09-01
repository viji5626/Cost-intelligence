"""
Ingestion Data Models, Target Schemas, and Column Alias Dictionaries
Includes source-wise utility aliases for Electricity (Grid/DG/Solar), Water (Borewell/PWD/Other),
Compressed Air, and Natural Gas/Fuel.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IngestionTarget(str, Enum):
    PLANT_OPEX = "PLANT_OPEX"
    VEHICLE_BOM = "VEHICLE_BOM"
    COMPONENT_COST = "COMPONENT_COST"
    ENGINEERING_CHANGE = "ENGINEERING_CHANGE"
    IDEATHON_RAW = "IDEATHON_RAW"


class ValidationSeverity(str, Enum):
    VALID = "VALID"
    UNUSUAL_VALID_DATA = "UNUSUAL_VALID_DATA"
    INVALID_DATA = "INVALID_DATA"


class RowValidationResult(BaseModel):
    row_number: int
    severity: ValidationSeverity
    raw_data: Dict[str, Any]
    cleaned_data: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    anomaly_flags: List[str] = Field(default_factory=list)


class IngestionBatchSummary(BaseModel):
    ingestion_id: str
    target: IngestionTarget
    filename: str
    file_hash: str
    total_rows: int
    valid_rows: int
    unusual_rows: int
    rejected_rows: int
    duration_ms: float
    status: str  # COMPLETED, COMPLETED_WITH_WARNINGS, FAILED_REJECTED
    rejected_details: List[RowValidationResult] = Field(default_factory=list)
    unusual_details: List[RowValidationResult] = Field(default_factory=list)


# Column Alias Dictionaries for Intelligent Mapping
COLUMN_ALIASES: Dict[IngestionTarget, Dict[str, List[str]]] = {
    IngestionTarget.PLANT_OPEX: {
        "plant_code": ["plant_code", "plant_id", "plant", "unit", "facility_code", "factory"],
        "period": ["period", "month", "date", "month_year", "period_date", "financial_period"],
        "production_quantity": ["production_quantity", "prod_qty", "volume", "vehicles_produced", "production_vol", "units"],
        
        # Electricity & Captive Generation
        "electricity_kwh": ["electricity_kwh", "power_kwh", "kwh", "electricity_units", "grid_power_kwh", "units_consumed", "total_kwh"],
        "electricity_cost": ["electricity_cost", "power_cost", "electricity_inr", "power_expense", "power_rs", "total_electricity_cost"],
        "grid_kwh": ["grid_kwh", "grid_power_kwh", "electricity_board_kwh", "purchased_kwh", "eb_kwh", "discom_kwh", "grid_units", "grid_electricity"],
        "grid_cost_inr": ["grid_cost_inr", "grid_cost", "eb_cost", "purchased_power_cost", "grid_inr", "eb_inr"],
        "dg_kwh": ["dg_kwh", "dg_generation", "dg_units", "diesel_generator_kwh", "dg_power_kwh", "generator_kwh", "dg_generated_kwh"],
        "dg_cost_inr": ["dg_cost_inr", "dg_cost", "dg_generation_cost", "dg_fuel_cost", "diesel_cost"],
        "solar_kwh": ["solar_kwh", "solar_generation", "solar_units", "solar_power_kwh", "rooftop_solar_kwh", "captive_solar_kwh", "solar_generated_kwh"],
        "solar_cost_inr": ["solar_cost_inr", "solar_cost", "solar_amortization", "solar_inr"],
        "other_generated_kwh": ["other_generated_kwh", "other_generation", "captive_other_kwh", "cogen_kwh", "biomass_kwh"],
        "other_generation_cost_inr": ["other_generation_cost_inr", "other_generation_cost", "other_captive_cost"],

        # Water Domain
        "water_kl": ["water_kl", "water_consumption_kl", "water_volume_kl", "kl", "water_consumed", "total_water_kl"],
        "water_cost": ["water_cost", "water_inr", "water_expense", "water_rs", "total_water_cost"],
        "borewell_kl": ["borewell_kl", "groundwater_kl", "borewell_water_kl", "tube_well_kl", "ground_water_kl", "borewell_water"],
        "borewell_cost_inr": ["borewell_cost_inr", "borewell_cost", "groundwater_cost", "borewell_inr"],
        "pwd_kl": ["pwd_kl", "government_water_kl", "municipal_water_kl", "pwd_water_kl", "govt_supply_kl", "midc_kl", "hsiidc_kl"],
        "pwd_cost_inr": ["pwd_cost_inr", "pwd_cost", "govt_water_cost", "municipal_water_cost"],
        "other_water_kl": ["other_water_kl", "tanker_water_kl", "ro_water_kl", "treated_water_kl", "recycled_water_kl"],
        "other_water_cost_inr": ["other_water_cost_inr", "other_water_cost", "tanker_cost"],

        # Compressed Air
        "compressed_air_nm3": ["compressed_air_nm3", "air_nm3", "compressed_air", "air_consumed"],
        "compressed_air_cost": ["compressed_air_cost", "air_cost", "air_inr"],
        "compressed_air_cf_total": [
            "compressed_air_cf_total",
            "compressed_air",
            "compressed_air_consumption",
            "compressed_air_volume",
            "compressed_air_cf",
            "air_consumption_cf",
            "air_volume_cf",
            "air_consumption",
            "total_air_cf",
            "air_cf",
        ],
        "compressor_kwh_total": [
            "compressor_kwh_total",
            "compressor_energy",
            "compressor_kwh",
            "compressed_air_kwh",
            "compressor_power_kwh",
            "air_compressor_kwh",
            "compressor_electricity_kwh",
        ],
        "compressed_air_cost_inr": [
            "compressed_air_cost_inr",
            "compressed_air_cost",
            "air_cost",
            "air_inr",
            "compressed_air_rs",
            "compressor_cost",
        ],
        "compressed_air_cf_per_vehicle": [
            "compressed_air_cf_per_vehicle",
            "cf_per_vehicle",
            "cf_per_veh",
            "compressed_air_cf_vehicle",
            "air_cf_per_vehicle",
        ],
        "compressor_kwh_per_cf": ["compressor_kwh_per_cf", "kwh_per_cf", "kwh_cf"],
        "compressor_cf_per_kwh": ["compressor_cf_per_kwh", "cf_per_kwh", "cf_kwh"],

        # Natural Gas / Fuel
        "gas_consumption_nm3": ["gas_consumption_nm3", "gas_nm3", "png_nm3", "lpg_kg", "gas_consumed", "fuel_nm3", "gas_consumption"],
        "gas_cost": ["gas_cost", "gas_inr", "fuel_cost", "gas_rs", "png_cost"],
        "gas_cf_total": ["gas_cf_total", "gas_cf", "natural_gas_cf", "png_cf", "gas_consumption_cf", "fuel_cf", "gas_volume_cf"],
        "gas_source_type": ["gas_source_type", "fuel_type", "gas_type", "fuel_source", "gas_category"],

        # Operations & Maintenance
        "waste_quantity_mt": ["waste_quantity_mt", "waste_mt", "waste_tons", "hazardous_waste_mt"],
        "waste_cost": ["waste_cost", "waste_inr", "waste_disposal_cost"],
        "labor_cost": ["labor_cost", "manpower_cost", "wages", "labor_inr", "salary_wages"],
        "maintenance_cost": ["maintenance_cost", "maint_cost", "spares_cost", "pm_cost", "maintenance_inr"],
        "other_opex": ["other_opex", "misc_opex", "overhead_opex", "admin_opex"],
        "total_opex": ["total_opex", "total_plant_cost", "gross_opex", "total_expense"],
    },
    IngestionTarget.VEHICLE_BOM: {
        "model_year_code": ["model_year_code", "model_year", "my_code", "year_code", "vehicle_model_year"],
        "part_number": ["part_number", "part_no", "part_code", "item_code", "material_number"],
        "quantity_per_vehicle": ["quantity_per_vehicle", "qty", "quantity", "qty_per_veh", "usage_qty"],
        "effective_from": ["effective_from", "valid_from", "start_date"],
        "effective_to": ["effective_to", "valid_to", "end_date"],
    },
    IngestionTarget.COMPONENT_COST: {
        "part_number": ["part_number", "part_no", "part_code", "item_code"],
        "plant_code": ["plant_code", "plant", "manufacturing_plant"],
        "period_start": ["period_start", "valid_from", "effective_date", "start_date"],
        "raw_material_cost": ["raw_material_cost", "rm_cost", "material_cost", "rm_inr"],
        "process_cost": ["process_cost", "machining_cost", "conversion_cost", "process_inr"],
        "overhead_cost": ["overhead_cost", "oh_cost", "plant_overhead"],
        "tool_amortization": ["tool_amortization", "tooling_cost", "amortization_per_pc"],
        "total_cost": ["total_cost", "piece_price", "po_price", "net_cost"],
    },
    IngestionTarget.ENGINEERING_CHANGE: {
        "ecn_number": ["ecn_number", "ecn_no", "eco_number", "change_notice_id", "cr_number"],
        "title": ["title", "change_title", "description_summary", "subject"],
        "release_date": ["release_date", "released_on", "ecn_date", "approval_date"],
        "change_category": ["change_category", "category", "type_of_change", "reason"],
        "affected_part_number": ["affected_part_number", "old_part_no", "existing_part_no", "affected_part"],
        "replaced_by_part_number": ["replaced_by_part_number", "new_part_no", "replacement_part_no", "superseding_part"],
        "estimated_saving_per_veh": ["estimated_saving_per_veh", "saving_per_veh", "cost_benefit_inr", "saving_inr"],
    },
    IngestionTarget.IDEATHON_RAW: {
        "idea_id": ["idea_id", "idea_no", "submission_id", "sr_no", "id"],
        "submitter_plant": ["submitter_plant", "plant", "location", "originating_plant"],
        "original_title": ["original_title", "title", "idea_title", "subject", "concept"],
        "original_description": ["original_description", "description", "idea_description", "problem_solution", "details"],
        "target_model_name": ["target_model_name", "model", "vehicle", "applicable_model"],
        "target_part_name": ["target_part_name", "part", "component", "part_name", "assembly"],
        "target_part_number": ["target_part_number", "part_number", "part_no", "drawing_no"],
        "claimed_saving_per_veh": ["claimed_saving_per_veh", "cost_saving", "saving_rs", "saving_inr", "expected_benefit"],
    },
}
