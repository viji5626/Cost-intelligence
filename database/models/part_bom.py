"""
Part, Subsystem, Assembly, Material, Supplier, and BOM Mapping Models
Implements engineering breakdown structure:
Subsystem -> Assembly -> Component -> Part -> Material & Supplier
and Bill of Materials (BOM) linking to Model Years.
"""

from typing import List, Optional
from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.models.base import BaseModel


class Subsystem(BaseModel):
    """Top-level automotive subsystem (e.g., Engine & Transmission, Frame & Chassis, Electrical, Braking)."""

    __tablename__ = "subsystems"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_safety_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    assemblies: Mapped[List["Assembly"]] = relationship("Assembly", back_populates="subsystem", cascade="all, delete-orphan")


class Assembly(BaseModel):
    """Major assembly group (e.g., Front Fork Assembly, Crankcase Assembly, Wiring Harness)."""

    __tablename__ = "assemblies"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    subsystem_id: Mapped[str] = mapped_column(String(36), ForeignKey("subsystems.id", ondelete="CASCADE"), nullable=False)
    is_safety_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    subsystem: Mapped["Subsystem"] = relationship("Subsystem", back_populates="assemblies")
    components: Mapped[List["Component"]] = relationship("Component", back_populates="assembly", cascade="all, delete-orphan")


class Component(BaseModel):
    """Sub-assembly or functional component group (e.g., Brake Caliper, Cylinder Head, Starter Motor)."""

    __tablename__ = "components"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    assembly_id: Mapped[str] = mapped_column(String(36), ForeignKey("assemblies.id", ondelete="CASCADE"), nullable=False)
    is_safety_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    assembly: Mapped["Assembly"] = relationship("Assembly", back_populates="components")
    parts: Mapped[List["Part"]] = relationship("Part", back_populates="component", cascade="all, delete-orphan")


class Material(BaseModel):
    """Raw material grade specifications (e.g., ADC12 Aluminum, EN8 Steel, PP-GF30 Plastic)."""

    __tablename__ = "materials"

    material_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    material_category: Mapped[str] = mapped_column(String(50), default="METALLIC", nullable=False)  # METALLIC, POLYMER, RUBBER, COMPOSITE
    grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    density_g_cm3: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    base_rate_per_kg: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)

    # Relationships
    parts: Mapped[List["Part"]] = relationship("Part", back_populates="material")


class Supplier(BaseModel):
    """Vendor / Supplier master record."""

    __tablename__ = "suppliers"

    supplier_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(50), default="India", nullable=False)
    tier: Mapped[str] = mapped_column(String(20), default="TIER_1", nullable=False)  # TIER_1, TIER_2, TIER_3
    quality_rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Part(BaseModel):
    """Individual manufactured or purchased part (Standard 10-digit Hero part number format)."""

    __tablename__ = "parts"

    part_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    part_name: Mapped[str] = mapped_column(String(150), nullable=False)
    component_id: Mapped[str] = mapped_column(String(36), ForeignKey("components.id", ondelete="CASCADE"), nullable=False)
    material_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("materials.id", ondelete="SET NULL"), nullable=True)
    drawing_number: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_safety_critical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_proprietary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    make_or_buy: Mapped[str] = mapped_column(String(20), default="BUY", nullable=False)  # MAKE, BUY

    # Relationships
    component: Mapped["Component"] = relationship("Component", back_populates="parts")
    material: Mapped[Optional["Material"]] = relationship("Material", back_populates="parts")
    bom_items: Mapped[List["BomItem"]] = relationship("BomItem", back_populates="part", cascade="all, delete-orphan")
    costs: Mapped[List["ComponentCost"]] = relationship("ComponentCost", back_populates="part", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_parts_part_number_trgm", "part_number", postgresql_using="gin", postgresql_ops={"part_number": "gin_trgm_ops"}),
        Index("ix_parts_part_name_trgm", "part_name", postgresql_using="gin", postgresql_ops={"part_name": "gin_trgm_ops"}),
    )


class BomItem(BaseModel):
    """Bill of Materials (BOM) item mapping a specific Part to a Model Year with quantity."""

    __tablename__ = "bom_items"

    model_year_id: Mapped[str] = mapped_column(String(36), ForeignKey("model_years.id", ondelete="CASCADE"), nullable=False)
    part_id: Mapped[str] = mapped_column(String(36), ForeignKey("parts.id", ondelete="CASCADE"), nullable=False)
    quantity_per_vehicle: Mapped[float] = mapped_column(Numeric(10, 4), default=1.0, nullable=False)
    effective_from: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    effective_to: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    model_year: Mapped["ModelYear"] = relationship("ModelYear", back_populates="bom_items")  # type: ignore
    part: Mapped["Part"] = relationship("Part", back_populates="bom_items")

    __table_args__ = (
        UniqueConstraint("model_year_id", "part_id", name="uq_model_year_part"),
        Index("ix_bom_items_model_year_id", "model_year_id"),
        Index("ix_bom_items_part_id", "part_id"),
    )


class ComponentCost(BaseModel):
    """Piece-part cost breakdown with plant and temporal validity."""

    __tablename__ = "component_costs"

    part_id: Mapped[str] = mapped_column(String(36), ForeignKey("parts.id", ondelete="CASCADE"), nullable=False)
    plant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("plants.id", ondelete="SET NULL"), nullable=True)  # type: ignore
    period_start: Mapped[Date] = mapped_column(Date, nullable=False)
    period_end: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    raw_material_cost: Mapped[float] = mapped_column(Numeric(14, 4), default=0.0, nullable=False)
    process_cost: Mapped[float] = mapped_column(Numeric(14, 4), default=0.0, nullable=False)
    overhead_cost: Mapped[float] = mapped_column(Numeric(14, 4), default=0.0, nullable=False)
    tool_amortization: Mapped[float] = mapped_column(Numeric(14, 4), default=0.0, nullable=False)
    total_cost: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="INR", nullable=False)
    source_system: Mapped[str] = mapped_column(String(50), default="ERP_SAP", nullable=False)

    # Relationships
    part: Mapped["Part"] = relationship("Part", back_populates="costs")

    __table_args__ = (
        Index("ix_component_costs_part_period", "part_id", "period_start"),
    )
