"""
Vehicle Ideathon Data Models: Submissions, Taxonomy, Decision States, and Clustering
Strictly vehicle / product cost reduction domain models.
"""

from enum import Enum
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, Date, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.models.base import BaseModel

if TYPE_CHECKING:
    from database.models.governance import IdeaReviewRecord


class IdeaDecisionState(str, Enum):
    """Business decision lifecycle states for Ideathon ideas."""
    SUBMITTED = "SUBMITTED"                          # Initial received state
    UNDER_REVIEW = "UNDER_REVIEW"                    # In technical review
    ACCEPTED_FOR_STUDY = "ACCEPTED_FOR_STUDY"        # Approved for feasibility evaluation
    APPROVED_FOR_IMPLEMENTATION = "APPROVED"         # Approved for engineering implementation
    ON_HOLD = "ON_HOLD"                              # Temporarily deferred
    REJECTED = "REJECTED"                            # Formally rejected by committee
    SUPERSEDED = "SUPERSEDED"                        # Replaced by a newer / broader idea


class ImplementationEvidenceState(str, Enum):
    """
    Evidence-based implementation tracking states (Kept strictly separate from IdeaDecisionState).
    """
    NOT_EVALUATED = "NOT_EVALUATED"                  # Discovery not yet run
    NO_EVIDENCE_FOUND = "NO_EVIDENCE_FOUND"          # No ECN or part supersession discovered
    POTENTIAL_EVIDENCE = "POTENTIAL_EVIDENCE"        # Weak match or candidate change found
    PARTIALLY_CONFIRMED = "PARTIALLY_CONFIRMED"      # Evidence on 1 variant but not full portfolio
    IMPLEMENTATION_CONFIRMED = "IMPLEMENTED"         # ECN and production BOM match confirmed
    HISTORICAL_IMPLEMENTATION = "HISTORICAL"         # Implemented prior to idea submission
    CONFLICTING_EVIDENCE = "CONFLICTING"             # Contradictory change notice records
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT"           # Drawing/ECN data missing


class DataQualityStatus(str, Enum):
    """Data completeness and ambiguity states for submitted ideas."""
    COMPLETE = "COMPLETE"                            # Fully resolved vehicle & part
    AMBIGUOUS_VEHICLE = "AMBIGUOUS_VEHICLE"          # Mentioned generic or multiple possible models
    AMBIGUOUS_COMPONENT = "AMBIGUOUS_COMPONENT"      # Description lacks clear part/drawing identification
    MISSING_DATA = "MISSING_DATA"                    # Missing critical description or claim
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"  # Low confidence extraction (< 0.65)


class CostReductionCategory(str, Enum):
    """Cost reduction taxonomy categories."""
    MATERIAL_SUBSTITUTION = "MATERIAL_SUBSTITUTION"  # E.g. Aluminum to Engineered Polymer, Steel grade optimization
    GEOMETRY_OPTIMIZATION = "GEOMETRY_OPTIMIZATION"  # Rib reduction, wall thickness optimization, weight reduction
    FASTENER_CONSOLIDATION = "FASTENER_CONSOLIDATION"# M6 screw consolidation, clip replacement
    PROCESS_SIMPLIFICATION = "PROCESS_SIMPLIFICATION"# Eliminating machining pass, mold cycle reduction
    LOCAL_SOURCING = "LOCAL_SOURCING"                # Import substitution, supplier localization
    PACKAGING_LOGISTICS = "PACKAGING_LOGISTICS"      # Returnable bins, nesting optimization
    FEATURE_RATIONALIZATION = "FEATURE_RATIONALIZATION"# Eliminating redundant brackets or stickers
    OTHER_VAVE = "OTHER_VAVE"                        # General Value Analysis / Value Engineering


class OpportunityStatus(str, Enum):
    """Status of deterministic vehicle cost opportunity calculation."""
    CALCULATED = "CALCULATED"                        # Complete valid opportunity calculation
    MISSING_BOM_COST = "MISSING_BOM_COST"            # Base part cost missing in ERP/PLM BOM
    UNQUANTIFIED = "UNQUANTIFIED"                    # Idea does not propose quantifiable saving or proposed cost
    INSUFFICIENT_VOLUME_DATA = "INSUFFICIENT_VOLUME_DATA" # Applicable models have 0 volume records
    NEGATIVE_SAVING = "NEGATIVE_SAVING"              # Proposed cost exceeds current baseline cost
    NO_OPPORTUNITY = "NO_OPPORTUNITY"                # Zero saving per vehicle


class IdeaSubmission(BaseModel):
    """
    Vehicle Ideathon Idea Submission.
    Preserves immutable raw submission text alongside normalized engineering taxonomy.
    """

    __tablename__ = "idea_submissions"

    submission_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    
    # 1. Immutable Raw Submission Text (Never altered)
    raw_title: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_description: Mapped[str] = mapped_column(Text, nullable=False)
    submitter_employee_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    submitter_plant_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    raw_claimed_saving_per_veh: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)

    # 2. Decomposed Problem & Proposed Solution
    decomposed_problem: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decomposed_solution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decomposed_expected_benefit: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 3. Normalized Engineering Taxonomy & Hierarchy Links
    target_vehicle_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True)
    target_model_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("vehicle_models.id", ondelete="SET NULL"), nullable=True)
    target_variant_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("vehicle_variants.id", ondelete="SET NULL"), nullable=True)
    target_subsystem_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("subsystems.id", ondelete="SET NULL"), nullable=True)
    target_assembly_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("assemblies.id", ondelete="SET NULL"), nullable=True)
    target_component_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("components.id", ondelete="SET NULL"), nullable=True)
    target_part_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("parts.id", ondelete="SET NULL"), nullable=True)

    extracted_part_number: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    extracted_part_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    extracted_synonyms: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)

    # 4. Classification & Category
    is_bom_linked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cost_reduction_category: Mapped[str] = mapped_column(String(50), default=CostReductionCategory.OTHER_VAVE.value, nullable=False)

    # 5. Dual States: Decision Lifecycle vs Evidence State
    decision_state: Mapped[str] = mapped_column(String(50), default=IdeaDecisionState.SUBMITTED.value, index=True, nullable=False)
    evidence_state: Mapped[str] = mapped_column(String(50), default=ImplementationEvidenceState.NOT_EVALUATED.value, index=True, nullable=False)
    data_quality: Mapped[str] = mapped_column(String(50), default=DataQualityStatus.COMPLETE.value, index=True, nullable=False)

    # 6. Confidence Metrics & Governance
    extraction_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    part_match_confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    verified_saving_per_veh: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    cluster_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("idea_clusters.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    cluster: Mapped[Optional["IdeaCluster"]] = relationship("IdeaCluster", back_populates="ideas")
    duplicate_links: Mapped[List["IdeaDuplicateLink"]] = relationship(
        "IdeaDuplicateLink",
        primaryjoin="IdeaSubmission.id == IdeaDuplicateLink.source_idea_id",
        cascade="all, delete-orphan",
    )
    opportunity_evaluation: Mapped[Optional["IdeaOpportunityEvaluation"]] = relationship(
        "IdeaOpportunityEvaluation",
        back_populates="idea",
        uselist=False,
        cascade="all, delete-orphan",
    )
    review_record: Mapped[Optional["IdeaReviewRecord"]] = relationship(
        "IdeaReviewRecord",
        back_populates="idea",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_idea_submissions_title_trgm", "raw_title", postgresql_using="gin", postgresql_ops={"raw_title": "gin_trgm_ops"}),
        Index("ix_idea_submissions_part_trgm", "extracted_part_number", postgresql_using="gin", postgresql_ops={"extracted_part_number": "gin_trgm_ops"}),
    )


class IdeaCluster(BaseModel):
    """
    Cluster grouping of similar, identical, or synergistic ideas targeting the same component/subsystem.
    """

    __tablename__ = "idea_clusters"

    cluster_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    primary_part_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("parts.id", ondelete="SET NULL"), nullable=True)
    primary_subsystem_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("subsystems.id", ondelete="SET NULL"), nullable=True)
    primary_category: Mapped[str] = mapped_column(String(50), default=CostReductionCategory.OTHER_VAVE.value, nullable=False)
    idea_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    ideas: Mapped[List["IdeaSubmission"]] = relationship("IdeaSubmission", back_populates="cluster")


class IdeaDuplicateLink(BaseModel):
    """
    Duplicate or synergistic cross-link between two idea submissions with similarity metric.
    """

    __tablename__ = "idea_duplicate_links"

    source_idea_id: Mapped[str] = mapped_column(String(36), ForeignKey("idea_submissions.id", ondelete="CASCADE"), nullable=False)
    target_idea_id: Mapped[str] = mapped_column(String(36), ForeignKey("idea_submissions.id", ondelete="CASCADE"), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 to 1.0
    duplicate_type: Mapped[str] = mapped_column(String(50), default="NEAR_DUPLICATE_SAME_VEHICLE", nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("source_idea_id", "target_idea_id", name="uq_idea_duplicate_pair"),
        Index("ix_duplicate_links_pair", "source_idea_id", "target_idea_id"),
    )


class IdeaOpportunityEvaluation(BaseModel):
    """
    Deterministic Vehicle Cost Opportunity Evaluation with Audit Provenance.
    """

    __tablename__ = "idea_opportunity_evaluations"

    idea_id: Mapped[str] = mapped_column(String(36), ForeignKey("idea_submissions.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=OpportunityStatus.CALCULATED.value, index=True, nullable=False)

    # Deterministic Cost Components (INR)
    current_piece_cost_inr: Mapped[Optional[float]] = mapped_column(Numeric(14, 4), nullable=True)
    proposed_piece_cost_inr: Mapped[Optional[float]] = mapped_column(Numeric(14, 4), nullable=True)
    saving_per_vehicle_inr: Mapped[Optional[float]] = mapped_column(Numeric(14, 4), nullable=True)

    # Volume & Financial Opportunities
    applicable_annual_volume: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gross_annual_opportunity_inr: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)
    tooling_investment_inr: Mapped[float] = mapped_column(Numeric(16, 4), default=0.0, nullable=False)
    validation_investment_inr: Mapped[float] = mapped_column(Numeric(16, 4), default=0.0, nullable=False)
    net_opportunity_inr: Mapped[Optional[float]] = mapped_column(Numeric(16, 4), nullable=True)

    # Payback Metrics
    payback_period_years: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    payback_period_months: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Applicability & Provenance
    applicable_models: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    volume_by_model: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)
    effective_model_year: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    formula_version: Mapped[str] = mapped_column(String(50), default="V1.0_DETERMINISTIC", nullable=False)
    provenance_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    provenance_metadata: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)

    # Relationships
    idea: Mapped["IdeaSubmission"] = relationship("IdeaSubmission", back_populates="opportunity_evaluation")
