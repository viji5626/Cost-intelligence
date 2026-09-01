"""
Plant Master, Production Volume, OPEX Records, and Benchmark Models
Implements Plant Operational Expenditure data model with multi-source utility tracking
(Electricity: Grid/DG/Solar; Water: Borewell/PWD/Other; Compressed Air; Gas/Fuel)
and multi-factor benchmark methodology with strict double-counting controls.
"""

from typing import List, Optional
from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.models.base import BaseModel


class Plant(BaseModel):
    """Hero manufacturing plant location (e.g., Haridwar, Dharuhera, Gurgaon, Neemrana, Halol, Chittoor)."""

    __tablename__ = "plants"

    plant_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(50), default="India", nullable=False)
    manufacturing_scope: Mapped[str] = mapped_column(String(100), default="FULL_VEHICLE_ASSEMBLY", nullable=False)
    annual_capacity_vehicles: Mapped[int] = mapped_column(Integer, default=1000000, nullable=False)
    operating_days_per_year: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    shifts_per_day: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    grid_tariff_inr_kwh: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    opex_records: Mapped[List["OpexRecord"]] = relationship("OpexRecord", back_populates="plant", cascade="all, delete-orphan")
    production_records: Mapped[List["ProductionRecord"]] = relationship("ProductionRecord", back_populates="plant", cascade="all, delete-orphan")
    benchmarks: Mapped[List["BenchmarkRecord"]] = relationship("BenchmarkRecord", back_populates="plant", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_plants_name_trgm", "name", postgresql_using="gin", postgresql_ops={"name": "gin_trgm_ops"}),
    )


class ProductionRecord(BaseModel):
    """Actual monthly/quarterly production volume by plant and vehicle model year."""

    __tablename__ = "production_records"

    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)
    model_year_id: Mapped[str] = mapped_column(String(36), ForeignKey("model_years.id", ondelete="CASCADE"), nullable=False)
    period: Mapped[Date] = mapped_column(Date, nullable=False)  # First day of the month/quarter
    actual_volume: Mapped[int] = mapped_column(Integer, nullable=False)
    planned_volume: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    operating_days: Mapped[int] = mapped_column(Integer, default=25, nullable=False)

    # Relationships
    plant: Mapped["Plant"] = relationship("Plant", back_populates="production_records")

    __table_args__ = (
        UniqueConstraint("plant_id", "model_year_id", "period", name="uq_plant_model_period"),
        Index("ix_production_records_period", "period"),
    )


class OpexRecord(BaseModel):
    """Plant operational expenditure and multi-source utility consumption records with derived KPIs."""

    __tablename__ = "opex_records"

    plant_id: Mapped[str] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)
    period: Mapped[Date] = mapped_column(Date, nullable=False)  # Monthly date (e.g. 2024-04-01)
    production_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # 1. Electricity & Energy Domain (Primary & Source Breakdown)
    electricity_kwh: Mapped[float] = mapped_column(Numeric(16, 4), default=0.0, nullable=False)
    electricity_cost: Mapped[float] = mapped_column(Numeric(16, 4), default=0.0, nullable=False)
    grid_kwh: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    grid_cost_inr: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    dg_kwh: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    dg_cost_inr: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    solar_kwh: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    solar_cost_inr: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    other_generated_kwh: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    other_generation_cost_inr: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    total_energy_kwh: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)

    # 2. Water Domain (Primary & Source Breakdown)
    water_kl: Mapped[float] = mapped_column(Numeric(16, 4), default=0.0, nullable=False)
    water_cost: Mapped[float] = mapped_column(Numeric(16, 4), default=0.0, nullable=False)
    borewell_kl: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    borewell_cost_inr: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    pwd_kl: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    pwd_cost_inr: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    other_water_kl: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    other_water_cost_inr: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)

    # 3. Compressed Air Utility Domain
    compressed_air_nm3: Mapped[float] = mapped_column(Numeric(16, 4), default=0.0, nullable=False)
    compressed_air_cost: Mapped[float] = mapped_column(Numeric(16, 4), default=0.0, nullable=False)
    compressed_air_cf_total: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    compressor_kwh_total: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    compressed_air_cost_allocated: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    is_compressor_power_embedded: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # 4. Natural Gas / Fuel Domain
    gas_consumption_nm3: Mapped[float] = mapped_column(Numeric(16, 4), default=0.0, nullable=False)
    gas_cost: Mapped[float] = mapped_column(Numeric(16, 4), default=0.0, nullable=False)
    gas_cf_total: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    gas_source_type: Mapped[str] = mapped_column(String(50), default="PNG", nullable=False)

    # 5. Operations & Maintenance
    waste_quantity_mt: Mapped[float] = mapped_column(Numeric(16, 4), default=0.0, nullable=False)
    waste_cost: Mapped[float] = mapped_column(Numeric(16, 4), default=0.0, nullable=False)
    labor_cost: Mapped[float] = mapped_column(Numeric(16, 4), default=0.0, nullable=False)
    maintenance_cost: Mapped[float] = mapped_column(Numeric(16, 4), default=0.0, nullable=False)
    other_opex: Mapped[float] = mapped_column(Numeric(16, 4), default=0.0, nullable=False)
    total_opex: Mapped[float] = mapped_column(Numeric(16, 4), nullable=False)

    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), default="SAP_CO_PLANT", nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(50), default="VERIFIED", nullable=False)

    # Relationships
    plant: Mapped["Plant"] = relationship("Plant", back_populates="opex_records")

    __table_args__ = (
        UniqueConstraint("plant_id", "period", name="uq_plant_opex_period"),
        Index("ix_opex_records_plant_period", "plant_id", "period"),
    )


class BenchmarkRecord(BaseModel):
    """Multi-mode OPEX benchmark targets and comparative baselines across utility dimensions."""

    __tablename__ = "benchmark_records"

    benchmark_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    benchmark_name: Mapped[str] = mapped_column(String(100), nullable=False)
    benchmark_type: Mapped[str] = mapped_column(String(50), nullable=False)  # BEST_COMPARABLE, PEER_GROUP, HISTORICAL_BASELINE, MANAGEMENT_TARGET
    plant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("plants.id", ondelete="SET NULL"), nullable=True)
    period: Mapped[Date] = mapped_column(Date, nullable=False)

    # Target KPIs
    kwh_per_vehicle: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    kl_per_vehicle: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    gas_cf_per_vehicle: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    opex_per_vehicle: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    
    # Target Utility Dimensions
    compressed_air_cf_per_vehicle: Mapped[Optional[float]] = mapped_column(Numeric(14, 4), nullable=True)
    compressor_kwh_per_cf: Mapped[Optional[float]] = mapped_column(Numeric(14, 6), nullable=True)
    compressor_cf_per_kwh: Mapped[Optional[float]] = mapped_column(Numeric(14, 4), nullable=True)
    
    comparability_index: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    plant: Mapped[Optional["Plant"]] = relationship("Plant", back_populates="benchmarks")

    __table_args__ = (
        Index("ix_benchmark_records_type", "benchmark_type"),
    )
