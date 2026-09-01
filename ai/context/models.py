"""
Context Management & Token Budgeter Data Models & Specifications
Canonical schemas for evidence items, authority hierarchy, token budgets, and context assembly.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceAuthorityEnum(str, Enum):
    """Hierarchical authority classes for engineering and financial evidence."""
    AUTHORITATIVE_ENGINEERING = "AUTHORITATIVE_ENGINEERING"    # Approved ECN, Certified Test Reports (Weight: 1.0)
    BOM_MASTER_DATA = "BOM_MASTER_DATA"                        # ERP BOM, Part Master Lineage (Weight: 0.90)
    PLANT_OPEX_ACTUALS = "PLANT_OPEX_ACTUALS"                  # Metered utility bills, monthly plant KPIs (Weight: 0.85)
    HISTORICAL_IMPLEMENTATION = "HISTORICAL_IMPLEMENTATION"    # Verified past cost project closures (Weight: 0.75)
    IDEATHON_SUBMISSION = "IDEATHON_SUBMISSION"                # Unverified employee crowd ideas (Weight: 0.50)
    SECONDARY_EXTERNAL = "SECONDARY_EXTERNAL"                  # Vendor catalog notes / unverified web (Weight: 0.35)

    @property
    def weight(self) -> float:
        weights = {
            SourceAuthorityEnum.AUTHORITATIVE_ENGINEERING: 1.0,
            SourceAuthorityEnum.BOM_MASTER_DATA: 0.90,
            SourceAuthorityEnum.PLANT_OPEX_ACTUALS: 0.85,
            SourceAuthorityEnum.HISTORICAL_IMPLEMENTATION: 0.75,
            SourceAuthorityEnum.IDEATHON_SUBMISSION: 0.50,
            SourceAuthorityEnum.SECONDARY_EXTERNAL: 0.35,
        }
        return weights.get(self, 0.50)


class CountingModeEnum(str, Enum):
    """Token counting method classification."""
    EXACT_TOKEN_COUNT = "EXACT_TOKEN_COUNT"
    ESTIMATED_TOKEN_COUNT = "ESTIMATED_TOKEN_COUNT"


class PlacementEnum(str, Enum):
    """Lost-in-the-middle controlled placement positions."""
    BEGINNING = "BEGINNING"  # Top authoritative evidence & primary context
    MIDDLE = "MIDDLE"        # Supporting context & background facts
    END = "END"              # Critical constraints, conflicting evidence & instructions closest to user prompt


class OverflowStatusEnum(str, Enum):
    """Context budget fitting status."""
    FIT = "FIT"                          # All evidence fits comfortably within budget
    OVERFLOW_REDUCED = "OVERFLOW_REDUCED"  # Lower-priority evidence pruned to fit budget
    INSUFFICIENT_CONTEXT = "INSUFFICIENT_CONTEXT"  # Mandatory context exceeds model limit


class ContextItem(BaseModel):
    """Single evidence chunk prepared for context insertion with rich lineage."""
    source_id: str
    source_type: str  # ECN, PART_BOM, PLANT_OPEX, IDEATHON
    authority_class: SourceAuthorityEnum = SourceAuthorityEnum.SECONDARY_EXTERNAL
    text: str
    token_count: int
    counting_mode: CountingModeEnum = CountingModeEnum.ESTIMATED_TOKEN_COUNT
    original_rank: int = 1
    rerank_score: float = 0.50
    composite_priority: float = 0.50
    placement: PlacementEnum = PlacementEnum.MIDDLE
    is_conflicting: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TokenBudgetSpec(BaseModel):
    """Dynamic token budget allocation for generative SLM execution."""
    model_id: str
    model_context_limit: int = 4096
    system_tokens: int = 256
    user_tokens: int = 128
    reserved_output_tokens: int = 512
    safety_reserve_tokens: int = 64
    max_evidence_tokens: int = 3136
    counting_mode: CountingModeEnum = CountingModeEnum.ESTIMATED_TOKEN_COUNT


class ContextBuildResult(BaseModel):
    """Complete structured artifact of assembled context with full provenance."""
    request_id: str
    model_id: str
    model_context_limit: int
    counting_mode: CountingModeEnum
    system_tokens: int
    user_tokens: int
    evidence_tokens: int
    reserved_output_tokens: int
    safety_reserve_tokens: int
    total_used_tokens: int
    remaining_available_tokens: int
    selected_items: List[ContextItem] = Field(default_factory=list)
    excluded_items: List[Dict[str, Any]] = Field(default_factory=list)
    exclusion_reasons: Dict[str, str] = Field(default_factory=dict)
    assembled_prompt: str
    overflow_status: OverflowStatusEnum = OverflowStatusEnum.FIT
    has_conflicting_evidence: bool = False
    context_version: str = "v1.0"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: Dict[str, Any] = Field(default_factory=dict)
