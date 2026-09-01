"""
Evidence Grounding & Multi-Horizon Retrieval Evaluation Models
Defines canonical schemas for the 7 Implementation Evidence States, 8 distinct evaluation dimensions,
claim-level verification, historical validity policies, and full retrieval provenance.
"""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ai.context.models import SourceAuthorityEnum
from database.models.ideathon import ImplementationEvidenceState


class EvidenceClassificationEnum(str, Enum):
    """Classification of individual retrieved evidence items relative to an engineering claim."""
    DIRECT_EVIDENCE = "DIRECT_EVIDENCE"              # Explicit ECN/BOM closure matching part and technical change
    SUPPORTING_EVIDENCE = "SUPPORTING_EVIDENCE"      # Certified test report, supplier specification, plant metric
    INDIRECT_EVIDENCE = "INDIRECT_EVIDENCE"          # Sibling model implementation, parent assembly change
    HISTORICAL_EVIDENCE = "HISTORICAL_EVIDENCE"      # Past cost reduction project or superseded ECN
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"    # Contradictory release vs obsolescence or competing ECN
    IRRELEVANT_EVIDENCE = "IRRELEVANT_EVIDENCE"      # Unrelated part or superficial semantic match
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # Low-confidence ambiguous candidate


class ImplementationDecisionEnum(str, Enum):
    """
    7 Canonical Implementation Evidence States.
    CRITICAL INVARIANT: NO_IMPLEMENTATION_EVIDENCE_FOUND != NOT_IMPLEMENTED.
    """
    IMPLEMENTATION_CONFIRMED = "IMPLEMENTATION_CONFIRMED"
    PARTIALLY_CONFIRMED = "PARTIALLY_CONFIRMED"
    HISTORICAL_IMPLEMENTATION = "HISTORICAL_IMPLEMENTATION"
    POTENTIAL_IMPLEMENTATION_EVIDENCE = "POTENTIAL_EVIDENCE"
    NO_IMPLEMENTATION_EVIDENCE_FOUND = "NO_EVIDENCE_FOUND"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


class ApplicabilityScopeEnum(str, Enum):
    """Dimension 5: Scope alignment across vehicle models, variants, and platforms."""
    EXACT_MODEL_MATCH = "EXACT_MODEL_MATCH"          # Evidence applies directly to target vehicle model
    CROSS_MODEL_APPLICABLE = "CROSS_MODEL_APPLICABLE"# Evidence on sibling model with confirmed part sharing
    CROSS_MODEL_UNCONFIRMED = "CROSS_MODEL_UNCONFIRMED"# Sibling model evidence without confirmed BOM sharing
    NOT_APPLICABLE = "NOT_APPLICABLE"                # Document pertains to distinct non-shared platform


class TemporalValidityEnum(str, Enum):
    """Dimension 6: Temporal status and lifecycle recency."""
    CURRENT_ACTIVE = "CURRENT_ACTIVE"                # Currently released and active in production BOM
    HISTORICAL_SUPERSEDED = "HISTORICAL_SUPERSEDED"  # Superseded by subsequent ECN or obsolete
    PREDATES_SUBMISSION = "PREDATES_SUBMISSION"      # Released prior to idea submission date
    FUTURE_EFFECTIVE = "FUTURE_EFFECTIVE"            # Scheduled for future model-year SOP
    TIME_UNKNOWN = "TIME_UNKNOWN"                    # No date metadata available on source record


class ImplementationRelationshipEnum(str, Enum):
    """Dimension 7: Technical equivalence vs superficial surface similarity."""
    DIRECT_CHANGE = "DIRECT_CHANGE"                  # Exact same engineering change on exact part
    PARTIAL_EQUIVALENT = "PARTIAL_EQUIVALENT"        # Equivalent goal via alternative technical mechanism
    TECHNICAL_DIFFERENT = "TECHNICAL_DIFFERENT"      # Similar text/goal but completely different engineering action
    CONTRADICTORY_CLAIM = "CONTRADICTORY_CLAIM"      # Explicit claim of rejection, rollback, or incompatibility
    IRRELEVANT = "IRRELEVANT"                        # No technical relationship


class HistoricalValidityPolicy(BaseModel):
    """Configurable, versioned policy for evaluating temporal validity across source types."""
    policy_version: str = "hist-v1.0.0"
    max_active_lifespan_years: Dict[str, int] = Field(
        default_factory=lambda: {
            "ECN": 5,
            "BOM": 3,
            "PLANT_OPEX": 2,
            "TEST_REPORT": 7,
            "HISTORICAL_PROJECT": 10,
        }
    )
    require_active_status_for_current: bool = True
    supersession_invalidates_current: bool = True


class GroundingEvaluationSpec(BaseModel):
    """Configuration parameters and thresholds for evidence grounding evaluation."""
    authority_policy_version: str = "v1.0.0"
    min_grounding_score: float = 0.70
    min_confidence_for_confirmation: float = 0.80
    exact_match_weight_multiplier: float = 1.25
    stale_index_threshold_hours: int = 168  # 7 days
    historical_policy: HistoricalValidityPolicy = Field(default_factory=HistoricalValidityPolicy)


class GroundingClaim(BaseModel):
    """Individual engineering claim extracted from query/task with verification status."""
    claim_id: str
    claim_text: str
    claim_category: str = "ENGINEERING_CHANGE"
    is_supported: bool = False
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    certainty: float = 0.0
    notes: str = ""


class ClassifiedEvidenceItem(BaseModel):
    """
    Enriched evidence record with explicit, unmerged 8-dimensional scores.
    """
    evidence_id: str
    source_id: str
    source_type: str  # ECN, BOM, PLANT_OPEX, TEST_REPORT, DRAWING
    code_or_number: str
    title: str
    snippet: str
    part_number: Optional[str] = None
    model_code: Optional[str] = None
    category: Optional[str] = None

    # The 8 Distinct Evaluation Dimensions (Never merged into a single scalar):
    dim1_retrieval_relevance: float = 0.0      # RRF score [0.0, 1.0]
    dim2_reranker_relevance: float = 0.0       # Cross-encoder score [0.0, 1.0]
    dim3_source_authority: float = 0.50        # Authority hierarchy weight [0.0, 1.0]
    dim4_evidence_strength: float = 0.50       # Evidentiary proof strength [0.0, 1.0]
    dim5_applicability: ApplicabilityScopeEnum = ApplicabilityScopeEnum.NOT_APPLICABLE
    dim6_temporal_validity: TemporalValidityEnum = TemporalValidityEnum.TIME_UNKNOWN
    dim7_implementation_relationship: ImplementationRelationshipEnum = ImplementationRelationshipEnum.IRRELEVANT
    dim8_grounding_contribution: float = 0.0   # Contribution to supported claims [0.0, 1.0]

    classification: EvidenceClassificationEnum = EvidenceClassificationEnum.INSUFFICIENT_EVIDENCE
    effective_date: Optional[str] = None
    is_historical: bool = False
    is_conflicting: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class FullRetrievalProvenance(BaseModel):
    """Complete diagnostic trace of query formulation, search channels, and evaluation decisions."""
    request_id: str
    idea_id: Optional[str] = None
    raw_query: str
    expanded_query_terms: List[str] = Field(default_factory=list)
    extracted_identifiers: Dict[str, Optional[str]] = Field(default_factory=dict)
    strategies_executed: List[str] = Field(default_factory=list)
    candidates_retrieved_count: int = 0
    candidates_reranked_count: int = 0
    context_items_selected_count: int = 0
    embedding_model_id: str = "native-local-embedding-v1"
    embedding_model_hash: str = "embed-hash-local-06"
    reranker_model_id: str = "native-local-cross-encoder-v1"
    reranker_model_hash: str = "rerank-hash-local-07"
    grounding_policy_version: str = "v1.0.0"
    authority_policy_version: str = "v1.0.0"
    historical_policy_version: str = "hist-v1.0.0"
    latency_breakdown_ms: Dict[str, float] = Field(default_factory=dict)
    stale_index_detected: bool = False
    stopping_reason: str = "NORMAL_COMPLETION"


class GroundingEvaluationResult(BaseModel):
    """
    Authoritative outcome of the Retrieval & Evidence Grounding Integration pass.
    """
    request_id: str
    idea_id: Optional[str] = None
    query: str
    decision: ImplementationDecisionEnum
    grounding_score: float = Field(
        ...,
        description="Ratio of material claims supported by verified retrieved evidence [0.0, 1.0]",
    )
    confidence_score: float = Field(
        ...,
        description="Evaluator confidence in the decision state assignment [0.0, 1.0]",
    )
    summary: str
    claims: List[GroundingClaim] = Field(default_factory=list)
    classified_evidences: List[ClassifiedEvidenceItem] = Field(default_factory=list)
    applicable_models_count: int = 0
    confirmed_models: List[str] = Field(default_factory=list)
    unconfirmed_models: List[str] = Field(default_factory=list)
    requires_human_review: bool = False
    review_reasons: List[str] = Field(default_factory=list)
    provenance: FullRetrievalProvenance
