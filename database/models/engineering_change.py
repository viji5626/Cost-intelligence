"""
Engineering Change Notices (ECN) and Implementation Discovery Models
Implements the 7-state implementation taxonomy:
IMPLEMENTATION_CONFIRMED, PARTIALLY_CONFIRMED, HISTORICAL_IMPLEMENTATION,
POTENTIAL_EVIDENCE, NO_EVIDENCE_FOUND, INSUFFICIENT_EVIDENCE, CONFLICTING_EVIDENCE
"""

from typing import List, Optional
from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.models.base import BaseModel


class EngineeringChange(BaseModel):
    """Engineering Change Notice / Order (ECN/ECO) record."""

    __tablename__ = "engineering_changes"

    ecn_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    release_date: Mapped[Date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="RELEASED", nullable=False)  # DRAFT, IN_REVIEW, RELEASED, OBSOLETE
    change_category: Mapped[str] = mapped_column(String(50), default="COST_REDUCTION", nullable=False)  # COST_REDUCTION, QUALITY, WEIGHT, REGULATORY
    affected_part_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("parts.id", ondelete="SET NULL"), nullable=True)
    replaced_by_part_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("parts.id", ondelete="SET NULL"), nullable=True)
    estimated_saving_per_veh: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    source_system: Mapped[str] = mapped_column(String(50), default="PLM_TEAMCENTER", nullable=False)

    # Relationships
    implementations: Mapped[List["Implementation"]] = relationship("Implementation", back_populates="engineering_change", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_ecn_number_trgm", "ecn_number", postgresql_using="gin", postgresql_ops={"ecn_number": "gin_trgm_ops"}),
        Index("ix_ecn_title_trgm", "title", postgresql_using="gin", postgresql_ops={"title": "gin_trgm_ops"}),
    )


class Implementation(BaseModel):
    """Verified production implementation state by plant, model year, and part."""

    __tablename__ = "implementations"

    engineering_change_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("engineering_changes.id", ondelete="SET NULL"), nullable=True)
    part_id: Mapped[str] = mapped_column(String(36), ForeignKey("parts.id", ondelete="CASCADE"), nullable=False)
    plant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=True)
    model_year_id: Mapped[str] = mapped_column(String(36), ForeignKey("model_years.id", ondelete="CASCADE"), nullable=False)
    
    # 7-State Taxonomy
    status: Mapped[str] = mapped_column(String(50), default="POTENTIAL_EVIDENCE", nullable=False)
    # Options: IMPLEMENTATION_CONFIRMED, PARTIALLY_CONFIRMED, HISTORICAL_IMPLEMENTATION,
    # POTENTIAL_EVIDENCE, NO_EVIDENCE_FOUND, INSUFFICIENT_EVIDENCE, CONFLICTING_EVIDENCE

    implementation_date: Mapped[Optional[Date]] = mapped_column(Date, nullable=True)
    cutoff_chassis_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cutoff_engine_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    verification_source: Mapped[str] = mapped_column(String(100), default="BOM_LINEAGE", nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.8, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    engineering_change: Mapped[Optional["EngineeringChange"]] = relationship("EngineeringChange", back_populates="implementations")

    __table_args__ = (
        Index("ix_implementations_part_model", "part_id", "model_year_id"),
        Index("ix_implementations_status", "status"),
    )
