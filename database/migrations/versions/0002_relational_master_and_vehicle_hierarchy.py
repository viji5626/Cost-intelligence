"""Relational Master Data and Vehicle Hierarchy Schema

Revision ID: 0002_vehicle_hierarchy
Revises: 0001_initial_schema
Create Date: 2026-08-31 17:52:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002_vehicle_hierarchy"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Product Families
    op.create_table(
        "product_families",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("family_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_product_families_id"), "product_families", ["id"], unique=False)
    op.create_index(op.f("ix_product_families_family_code"), "product_families", ["family_code"], unique=True)

    # 2. Vehicles
    op.create_table(
        "vehicles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("vehicle_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("product_family_id", sa.String(length=36), nullable=False),
        sa.Column("vehicle_type", sa.String(length=50), nullable=False, default="MOTORCYCLE"),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_family_id"], ["product_families.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vehicles_id"), "vehicles", ["id"], unique=False)
    op.create_index(op.f("ix_vehicles_vehicle_code"), "vehicles", ["vehicle_code"], unique=True)

    # 3. Vehicle Models
    op.create_table(
        "vehicle_models",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("model_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("vehicle_id", sa.String(length=36), nullable=False),
        sa.Column("platform_code", sa.String(length=50), nullable=True),
        sa.Column("start_year", sa.Integer(), nullable=True),
        sa.Column("end_year", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vehicle_models_id"), "vehicle_models", ["id"], unique=False)
    op.create_index(op.f("ix_vehicle_models_model_code"), "vehicle_models", ["model_code"], unique=True)
    op.create_index(op.f("ix_vehicle_models_platform_code"), "vehicle_models", ["platform_code"], unique=False)

    # 4. Vehicle Variants
    op.create_table(
        "vehicle_variants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("variant_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("model_id", sa.String(length=36), nullable=False),
        sa.Column("displacement_cc", sa.Float(), nullable=True),
        sa.Column("brake_type", sa.String(length=50), nullable=True),
        sa.Column("wheel_type", sa.String(length=50), nullable=True),
        sa.Column("fuel_type", sa.String(length=50), nullable=False, default="PETROL"),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_id"], ["vehicle_models.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vehicle_variants_id"), "vehicle_variants", ["id"], unique=False)
    op.create_index(op.f("ix_vehicle_variants_variant_code"), "vehicle_variants", ["variant_code"], unique=True)

    # 5. Model Generations
    op.create_table(
        "model_generations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("generation_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("variant_id", sa.String(length=36), nullable=False),
        sa.Column("start_year", sa.Integer(), nullable=False),
        sa.Column("end_year", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["variant_id"], ["vehicle_variants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_model_generations_id"), "model_generations", ["id"], unique=False)
    op.create_index(op.f("ix_model_generations_generation_code"), "model_generations", ["generation_code"], unique=True)

    # 6. Model Years
    op.create_table(
        "model_years",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("year_code", sa.String(length=50), nullable=False),
        sa.Column("generation_id", sa.String(length=36), nullable=False),
        sa.Column("calendar_year", sa.Integer(), nullable=False),
        sa.Column("annual_volume_planned", sa.Integer(), nullable=False, default=0),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["generation_id"], ["model_generations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("generation_id", "calendar_year", name="uq_generation_calendar_year"),
    )
    op.create_index(op.f("ix_model_years_id"), "model_years", ["id"], unique=False)
    op.create_index(op.f("ix_model_years_year_code"), "model_years", ["year_code"], unique=True)
    op.create_index("ix_model_years_calendar_year", "model_years", ["calendar_year"], unique=False)

    # 7. Engineering Structure: Subsystems, Assemblies, Components, Materials, Suppliers, Parts
    op.create_table(
        "subsystems",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_safety_critical", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_subsystems_id"), "subsystems", ["id"], unique=False)
    op.create_index(op.f("ix_subsystems_code"), "subsystems", ["code"], unique=True)

    op.create_table(
        "assemblies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("subsystem_id", sa.String(length=36), nullable=False),
        sa.Column("is_safety_critical", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["subsystem_id"], ["subsystems.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_assemblies_id"), "assemblies", ["id"], unique=False)
    op.create_index(op.f("ix_assemblies_code"), "assemblies", ["code"], unique=True)

    op.create_table(
        "components",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("assembly_id", sa.String(length=36), nullable=False),
        sa.Column("is_safety_critical", sa.Boolean(), nullable=False, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assembly_id"], ["assemblies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_components_id"), "components", ["id"], unique=False)
    op.create_index(op.f("ix_components_code"), "components", ["code"], unique=True)

    op.create_table(
        "materials",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("material_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("material_category", sa.String(length=50), nullable=False, default="METALLIC"),
        sa.Column("grade", sa.String(length=50), nullable=True),
        sa.Column("density_g_cm3", sa.Float(), nullable=True),
        sa.Column("base_rate_per_kg", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False, default="INR"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_materials_id"), "materials", ["id"], unique=False)
    op.create_index(op.f("ix_materials_material_code"), "materials", ["material_code"], unique=True)

    op.create_table(
        "suppliers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("supplier_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=50), nullable=False, default="India"),
        sa.Column("tier", sa.String(length=20), nullable=False, default="TIER_1"),
        sa.Column("quality_rating", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_suppliers_id"), "suppliers", ["id"], unique=False)
    op.create_index(op.f("ix_suppliers_supplier_code"), "suppliers", ["supplier_code"], unique=True)

    op.create_table(
        "parts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("part_number", sa.String(length=50), nullable=False),
        sa.Column("part_name", sa.String(length=150), nullable=False),
        sa.Column("component_id", sa.String(length=36), nullable=False),
        sa.Column("material_id", sa.String(length=36), nullable=True),
        sa.Column("drawing_number", sa.String(length=50), nullable=True),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("is_safety_critical", sa.Boolean(), nullable=False, default=False),
        sa.Column("is_proprietary", sa.Boolean(), nullable=False, default=False),
        sa.Column("make_or_buy", sa.String(length=20), nullable=False, default="BUY"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["component_id"], ["components.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["material_id"], ["materials.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_parts_id"), "parts", ["id"], unique=False)
    op.create_index(op.f("ix_parts_part_number"), "parts", ["part_number"], unique=True)
    op.create_index(op.f("ix_parts_drawing_number"), "parts", ["drawing_number"], unique=False)

    # 8. Plants
    op.create_table(
        "plants",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plant_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("location", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=False),
        sa.Column("country", sa.String(length=50), nullable=False, default="India"),
        sa.Column("manufacturing_scope", sa.String(length=100), nullable=False, default="FULL_VEHICLE_ASSEMBLY"),
        sa.Column("annual_capacity_vehicles", sa.Integer(), nullable=False, default=1000000),
        sa.Column("operating_days_per_year", sa.Integer(), nullable=False, default=300),
        sa.Column("shifts_per_day", sa.Integer(), nullable=False, default=3),
        sa.Column("grid_tariff_inr_kwh", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plants_id"), "plants", ["id"], unique=False)
    op.create_index(op.f("ix_plants_plant_code"), "plants", ["plant_code"], unique=True)

    # 9. BOM Items
    op.create_table(
        "bom_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("model_year_id", sa.String(length=36), nullable=False),
        sa.Column("part_id", sa.String(length=36), nullable=False),
        sa.Column("quantity_per_vehicle", sa.Numeric(precision=10, scale=4), nullable=False, default=1.0),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_year_id"], ["model_years.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["part_id"], ["parts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("model_year_id", "part_id", name="uq_model_year_part"),
    )
    op.create_index(op.f("ix_bom_items_id"), "bom_items", ["id"], unique=False)
    op.create_index("ix_bom_items_model_year_id", "bom_items", ["model_year_id"], unique=False)
    op.create_index("ix_bom_items_part_id", "bom_items", ["part_id"], unique=False)

    # 10. Component Costs
    op.create_table(
        "component_costs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("part_id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("raw_material_cost", sa.Numeric(precision=14, scale=4), nullable=False, default=0.0),
        sa.Column("process_cost", sa.Numeric(precision=14, scale=4), nullable=False, default=0.0),
        sa.Column("overhead_cost", sa.Numeric(precision=14, scale=4), nullable=False, default=0.0),
        sa.Column("tool_amortization", sa.Numeric(precision=14, scale=4), nullable=False, default=0.0),
        sa.Column("total_cost", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, default="INR"),
        sa.Column("source_system", sa.String(length=50), nullable=False, default="ERP_SAP"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["part_id"], ["parts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_component_costs_id"), "component_costs", ["id"], unique=False)
    op.create_index("ix_component_costs_part_period", "component_costs", ["part_id", "period_start"], unique=False)

    # 11. Production Records
    op.create_table(
        "production_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=False),
        sa.Column("model_year_id", sa.String(length=36), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("actual_volume", sa.Integer(), nullable=False),
        sa.Column("planned_volume", sa.Integer(), nullable=False, default=0),
        sa.Column("operating_days", sa.Integer(), nullable=False, default=25),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["model_year_id"], ["model_years.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plant_id", "model_year_id", "period", name="uq_plant_model_period"),
    )
    op.create_index(op.f("ix_production_records_id"), "production_records", ["id"], unique=False)
    op.create_index("ix_production_records_period", "production_records", ["period"], unique=False)

    # 12. OPEX Records
    op.create_table(
        "opex_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("production_quantity", sa.Integer(), nullable=False),
        sa.Column("electricity_kwh", sa.Numeric(precision=16, scale=4), nullable=False, default=0.0),
        sa.Column("electricity_cost", sa.Numeric(precision=16, scale=4), nullable=False, default=0.0),
        sa.Column("water_kl", sa.Numeric(precision=16, scale=4), nullable=False, default=0.0),
        sa.Column("water_cost", sa.Numeric(precision=16, scale=4), nullable=False, default=0.0),
        sa.Column("gas_consumption_nm3", sa.Numeric(precision=16, scale=4), nullable=False, default=0.0),
        sa.Column("gas_cost", sa.Numeric(precision=16, scale=4), nullable=False, default=0.0),
        sa.Column("compressed_air_nm3", sa.Numeric(precision=16, scale=4), nullable=False, default=0.0),
        sa.Column("compressed_air_cost", sa.Numeric(precision=16, scale=4), nullable=False, default=0.0),
        sa.Column("waste_quantity_mt", sa.Numeric(precision=16, scale=4), nullable=False, default=0.0),
        sa.Column("waste_cost", sa.Numeric(precision=16, scale=4), nullable=False, default=0.0),
        sa.Column("labor_cost", sa.Numeric(precision=16, scale=4), nullable=False, default=0.0),
        sa.Column("maintenance_cost", sa.Numeric(precision=16, scale=4), nullable=False, default=0.0),
        sa.Column("other_opex", sa.Numeric(precision=16, scale=4), nullable=False, default=0.0),
        sa.Column("total_opex", sa.Numeric(precision=16, scale=4), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, default="INR"),
        sa.Column("source_system", sa.String(length=50), nullable=False, default="SAP_CO_PLANT"),
        sa.Column("is_anomaly", sa.Boolean(), nullable=False, default=False),
        sa.Column("validation_status", sa.String(length=50), nullable=False, default="VERIFIED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plant_id", "period", name="uq_plant_opex_period"),
    )
    op.create_index(op.f("ix_opex_records_id"), "opex_records", ["id"], unique=False)
    op.create_index("ix_opex_records_plant_period", "opex_records", ["plant_id", "period"], unique=False)

    # 13. Benchmark Records
    op.create_table(
        "benchmark_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("benchmark_code", sa.String(length=50), nullable=False),
        sa.Column("benchmark_name", sa.String(length=100), nullable=False),
        sa.Column("benchmark_type", sa.String(length=50), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=True),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("kwh_per_vehicle", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("kl_per_vehicle", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("opex_per_vehicle", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("comparability_index", sa.Float(), nullable=False, default=1.0),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_benchmark_records_id"), "benchmark_records", ["id"], unique=False)
    op.create_index(op.f("ix_benchmark_records_benchmark_code"), "benchmark_records", ["benchmark_code"], unique=True)
    op.create_index("ix_benchmark_records_type", "benchmark_records", ["benchmark_type"], unique=False)

    # 14. Engineering Changes (ECN)
    op.create_table(
        "engineering_changes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("ecn_number", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, default="RELEASED"),
        sa.Column("change_category", sa.String(length=50), nullable=False, default="COST_REDUCTION"),
        sa.Column("affected_part_id", sa.String(length=36), nullable=True),
        sa.Column("replaced_by_part_id", sa.String(length=36), nullable=True),
        sa.Column("estimated_saving_per_veh", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("source_system", sa.String(length=50), nullable=False, default="PLM_TEAMCENTER"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["affected_part_id"], ["parts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["replaced_by_part_id"], ["parts.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_engineering_changes_id"), "engineering_changes", ["id"], unique=False)
    op.create_index(op.f("ix_engineering_changes_ecn_number"), "engineering_changes", ["ecn_number"], unique=True)

    # 15. Implementations
    op.create_table(
        "implementations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("engineering_change_id", sa.String(length=36), nullable=True),
        sa.Column("part_id", sa.String(length=36), nullable=False),
        sa.Column("plant_id", sa.String(length=36), nullable=True),
        sa.Column("model_year_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, default="POTENTIAL_EVIDENCE"),
        sa.Column("implementation_date", sa.Date(), nullable=True),
        sa.Column("cutoff_chassis_number", sa.String(length=50), nullable=True),
        sa.Column("cutoff_engine_number", sa.String(length=50), nullable=True),
        sa.Column("verification_source", sa.String(length=100), nullable=False, default="BOM_LINEAGE"),
        sa.Column("confidence_score", sa.Float(), nullable=False, default=0.8),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["engineering_change_id"], ["engineering_changes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["model_year_id"], ["model_years.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["part_id"], ["parts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plant_id"], ["plants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_implementations_id"), "implementations", ["id"], unique=False)
    op.create_index("ix_implementations_part_model", "implementations", ["part_id", "model_year_id"], unique=False)
    op.create_index("ix_implementations_status", "implementations", ["status"], unique=False)

    # 16. Create PostgreSQL Trigram Indexes if on postgresql dialect
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("CREATE INDEX IF NOT EXISTS ix_parts_part_number_trgm ON parts USING gin (part_number gin_trgm_ops);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_parts_part_name_trgm ON parts USING gin (part_name gin_trgm_ops);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_plants_name_trgm ON plants USING gin (name gin_trgm_ops);")
        op.execute("CREATE INDEX IF NOT EXISTS ix_ecn_number_trgm ON engineering_changes USING gin (ecn_number gin_trgm_ops);")


def downgrade() -> None:
    op.drop_table("implementations")
    op.drop_table("engineering_changes")
    op.drop_table("benchmark_records")
    op.drop_table("opex_records")
    op.drop_table("production_records")
    op.drop_table("component_costs")
    op.drop_table("bom_items")
    op.drop_table("plants")
    op.drop_table("parts")
    op.drop_table("suppliers")
    op.drop_table("materials")
    op.drop_table("components")
    op.drop_table("assemblies")
    op.drop_table("subsystems")
    op.drop_table("model_years")
    op.drop_table("model_generations")
    op.drop_table("vehicle_variants")
    op.drop_table("vehicle_models")
    op.drop_table("vehicles")
    op.drop_table("product_families")
