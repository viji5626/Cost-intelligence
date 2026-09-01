"""
Vehicle Hierarchy Relational Models
Implements the multi-tier vehicle product structure:
Product Family -> Vehicle -> Vehicle Model -> Vehicle Variant -> Model Generation -> Model Year
"""

from typing import List, Optional
from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.models.base import BaseModel


class ProductFamily(BaseModel):
    """Top-level portfolio category (e.g., Economy Commuter, Premium Sports, Scooter, EV)."""

    __tablename__ = "product_families"

    family_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    vehicles: Mapped[List["Vehicle"]] = relationship("Vehicle", back_populates="product_family", cascade="all, delete-orphan")


class Vehicle(BaseModel):
    """Vehicle entity (e.g., Splendor Series, HF Deluxe Series, Xpulse Series, Vida Series)."""

    __tablename__ = "vehicles"

    vehicle_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    product_family_id: Mapped[str] = mapped_column(String(36), ForeignKey("product_families.id", ondelete="CASCADE"), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(String(50), default="MOTORCYCLE", nullable=False)  # MOTORCYCLE, SCOOTER, EV
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    product_family: Mapped["ProductFamily"] = relationship("ProductFamily", back_populates="vehicles")
    models: Mapped[List["VehicleModel"]] = relationship("VehicleModel", back_populates="vehicle", cascade="all, delete-orphan")


class VehicleModel(BaseModel):
    """Specific vehicle commercial model (e.g., Splendor+, Splendor Pro, Xpulse 200)."""

    __tablename__ = "vehicle_models"

    model_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False)
    platform_code: Mapped[Optional[str]] = mapped_column(String(50), index=True, nullable=True)
    start_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="models")
    variants: Mapped[List["VehicleVariant"]] = relationship("VehicleVariant", back_populates="model", cascade="all, delete-orphan")


class VehicleVariant(BaseModel):
    """Variant specification (e.g., Drum/Alloy, Disc/Spoke, Self-Start, Connected Edition)."""

    __tablename__ = "vehicle_variants"

    variant_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_models.id", ondelete="CASCADE"), nullable=False)
    displacement_cc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    brake_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # DRUM, DISC, CBS, ABS
    wheel_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # ALLOY, SPOKE
    fuel_type: Mapped[str] = mapped_column(String(50), default="PETROL", nullable=False)  # PETROL, ELECTRIC, HYBRID
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    model: Mapped["VehicleModel"] = relationship("VehicleModel", back_populates="variants")
    generations: Mapped[List["ModelGeneration"]] = relationship("ModelGeneration", back_populates="variant", cascade="all, delete-orphan")


class ModelGeneration(BaseModel):
    """Major design generation / refresh cycle (e.g., Gen 1 (2018-2021), Gen 2 (2022-Present))."""

    __tablename__ = "model_generations"

    generation_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    variant_id: Mapped[str] = mapped_column(String(36), ForeignKey("vehicle_variants.id", ondelete="CASCADE"), nullable=False)
    start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    end_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    variant: Mapped["VehicleVariant"] = relationship("VehicleVariant", back_populates="generations")
    model_years: Mapped[List["ModelYear"]] = relationship("ModelYear", back_populates="generation", cascade="all, delete-orphan")


class ModelYear(BaseModel):
    """Specific commercial model year (e.g., MY2023, MY2024, MY2025) with planned volumes."""

    __tablename__ = "model_years"

    year_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("model_generations.id", ondelete="CASCADE"), nullable=False)
    calendar_year: Mapped[int] = mapped_column(Integer, nullable=False)
    annual_volume_planned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    generation: Mapped["ModelGeneration"] = relationship("ModelGeneration", back_populates="model_years")
    bom_items: Mapped[List["BomItem"]] = relationship("BomItem", back_populates="model_year", cascade="all, delete-orphan")  # type: ignore

    __table_args__ = (
        UniqueConstraint("generation_id", "calendar_year", name="uq_generation_calendar_year"),
        Index("ix_model_years_calendar_year", "calendar_year"),
    )
