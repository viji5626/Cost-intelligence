"""
Confidence Calibration & Review Prioritization Engine
Implements deterministic, evidence-grounded confidence scoring and multi-tier routing logic.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from database.models.governance import ConfidenceTier, ReviewPriority
from database.models.ideathon import DataQualityStatus, ImplementationEvidenceState


class CalibratedConfidenceResult(BaseModel):
    """Calibrated confidence evaluation output with factor-by-factor breakdown."""

    composite_score: float = Field(ge=0.0, le=1.0)
    confidence_tier: str
    source_authority_score: float
    exact_identifier_score: float
    retrieval_relevance_score: float
    corroboration_score: float
    evidence_completeness_score: float
    entity_resolution_score: float
    conflict_penalty_applied: float
    breakdown_metadata: Dict = Field(default_factory=dict)


class ReviewRoutingResult(BaseModel):
    """Deterministic review queue prioritization and explanation."""

    requires_human_review: bool
    review_priority: str
    is_safety_critical: bool
    routing_reasons: List[str] = Field(default_factory=list)


class ConfidenceCalibrationEngine:
    """
    Evidence-grounded confidence calibration engine.
    Forbids black-box uncalibrated numbers. Computes composite score from measurable evidence attributes.
    """

    # Defined safety-critical automotive subsystems
    SAFETY_CRITICAL_SUBSYSTEMS = {
        "BRAKES",
        "BRAKE_SYSTEM",
        "STEERING",
        "STEERING_SUSPENSION",
        "SUSPENSION",
        "FRAME",
        "CHASSIS_FRAME",
        "SAFETY",
    }

    @classmethod
    def calculate_confidence(
        cls,
        source_authority: str = "ERP_SAP",  # ERP_SAP, PLM_TEAMCENTER, DRAWING, CAD, DRAFT, UNOFFICIAL
        exact_identifier_matched: bool = True,
        is_synonym_match: bool = False,
        retrieval_relevance: float = 1.0,
        corroborating_sources_count: int = 1,
        has_ecn_record: bool = True,
        has_bom_record: bool = True,
        has_effective_dates: bool = True,
        entity_extraction_confidence: float = 1.0,
        has_conflicting_records: bool = False,
    ) -> CalibratedConfidenceResult:
        """
        Calculates calibrated composite score with strict deterministic weighting.
        """
        # 1. Source Authority Score (Weight 0.20)
        auth_upper = source_authority.upper()
        if auth_upper in ("ERP_SAP", "PLM_TEAMCENTER"):
            source_auth_score = 1.0
        elif auth_upper in ("DRAWING", "CAD"):
            source_auth_score = 0.90
        elif auth_upper == "DRAFT":
            source_auth_score = 0.50
        else:
            source_auth_score = 0.30

        # 2. Identifier Resolution Score (Weight 0.20)
        if exact_identifier_matched:
            ident_score = 1.0
        elif is_synonym_match:
            ident_score = 0.75
        else:
            ident_score = 0.40

        # 3. Retrieval Relevance Score (Weight 0.15)
        relevance_score = max(0.0, min(1.0, retrieval_relevance))

        # 4. Corroboration Score (Weight 0.15)
        if corroborating_sources_count >= 2:
            corrob_score = 1.0
        elif corroborating_sources_count == 1:
            corrob_score = 0.70
        else:
            corrob_score = 0.20

        # 5. Evidence Completeness Score (Weight 0.15)
        comp_parts = 0
        if has_ecn_record:
            comp_parts += 1
        if has_bom_record:
            comp_parts += 1
        if has_effective_dates:
            comp_parts += 1
        completeness_score = comp_parts / 3.0

        # 6. Entity Resolution Score (Weight 0.15)
        entity_score = max(0.0, min(1.0, entity_extraction_confidence))

        # Weighted Base Composite Calculation
        raw_composite = (
            (0.20 * source_auth_score)
            + (0.20 * ident_score)
            + (0.15 * relevance_score)
            + (0.15 * corrob_score)
            + (0.15 * completeness_score)
            + (0.15 * entity_score)
        )

        # Conflict Penalty Deduction
        conflict_penalty = 0.35 if has_conflicting_records else 0.0
        final_score = max(0.0, min(1.0, raw_composite - conflict_penalty))
        final_score = round(final_score, 4)

        # Tier Categorization
        if final_score >= 0.85:
            tier = ConfidenceTier.HIGH.value
        elif final_score >= 0.65:
            tier = ConfidenceTier.MEDIUM.value
        elif final_score >= 0.45:
            tier = ConfidenceTier.LOW.value
        else:
            tier = ConfidenceTier.VERY_LOW.value

        breakdown = {
            "source_authority": {"type": source_authority, "score": source_auth_score, "weight": 0.20},
            "identifier_match": {"exact": exact_identifier_matched, "score": ident_score, "weight": 0.20},
            "retrieval_relevance": {"score": relevance_score, "weight": 0.15},
            "corroboration": {"count": corroborating_sources_count, "score": corrob_score, "weight": 0.15},
            "evidence_completeness": {"score": completeness_score, "weight": 0.15},
            "entity_resolution": {"score": entity_score, "weight": 0.15},
            "conflict_penalty": conflict_penalty,
            "calibrated_tier": tier,
        }

        return CalibratedConfidenceResult(
            composite_score=final_score,
            confidence_tier=tier,
            source_authority_score=source_auth_score,
            exact_identifier_score=ident_score,
            retrieval_relevance_score=relevance_score,
            corroboration_score=corrob_score,
            evidence_completeness_score=completeness_score,
            entity_resolution_score=entity_score,
            conflict_penalty_applied=conflict_penalty,
            breakdown_metadata=breakdown,
        )


class ReviewPrioritizer:
    """
    Deterministic Review Prioritizer.
    Evaluates safety gates, conflict presence, financial scale, and confidence to assign priority tiers.
    """

    HIGH_VALUE_OPPORTUNITY_THRESHOLD_INR = 10000000.0  # ₹1 Crore Net Annual Opportunity

    @classmethod
    def evaluate_routing(
        cls,
        subsystem_code: Optional[str] = None,
        is_part_safety_critical: bool = False,
        evidence_state: str = ImplementationEvidenceState.NOT_EVALUATED.value,
        data_quality: str = DataQualityStatus.COMPLETE.value,
        calibrated_confidence_score: float = 1.0,
        net_opportunity_inr: Optional[float] = None,
        sibling_models_count: int = 1,
    ) -> ReviewRoutingResult:
        """
        Determines review requirement, priority tier, and comprehensive routing explanations.
        """
        reasons: List[str] = []
        is_safety = False

        # 1. Safety-Critical Automotive Subsystem Check (MANDATORY GATE)
        sub_upper = (subsystem_code or "").upper()
        if is_part_safety_critical or any(sc in sub_upper for sc in ConfidenceCalibrationEngine.SAFETY_CRITICAL_SUBSYSTEMS):
            is_safety = True
            reasons.append("SAFETY_CRITICAL_SYSTEM: Affects vehicle brakes, steering, suspension, or chassis frame.")

        # 2. Conflicting Implementation Evidence Check
        if evidence_state == ImplementationEvidenceState.CONFLICTING_EVIDENCE.value:
            reasons.append("CONFLICTING_EVIDENCE: Contradictory engineering change notices or status records found.")

        # 3. High Financial Value Opportunity Check
        if net_opportunity_inr and net_opportunity_inr >= cls.HIGH_VALUE_OPPORTUNITY_THRESHOLD_INR:
            reasons.append(f"HIGH_VALUE_OPPORTUNITY: Net annual opportunity (₹{net_opportunity_inr:,.2f}) exceeds ₹1 Crore threshold.")

        # 4. Low Confidence / Insufficient Evidence Check
        if calibrated_confidence_score < 0.65 or evidence_state == ImplementationEvidenceState.INSUFFICIENT_EVIDENCE.value:
            reasons.append(f"LOW_CONFIDENCE: Calibrated evidence confidence ({calibrated_confidence_score:.2f}) is below reliable threshold (0.65).")

        # 5. Ambiguous Taxonomy / Data Quality Check
        if data_quality in (
            DataQualityStatus.AMBIGUOUS_VEHICLE.value,
            DataQualityStatus.AMBIGUOUS_COMPONENT.value,
            DataQualityStatus.MISSING_DATA.value,
            DataQualityStatus.REQUIRES_HUMAN_REVIEW.value,
        ):
            reasons.append(f"AMBIGUOUS_TAXONOMY: Data quality flag [{data_quality}] requires technical specification clarification.")

        # 6. Cross-Model Sharing Portfolio Impact
        if sibling_models_count >= 3:
            reasons.append(f"CROSS_MODEL_PORTFOLIO_IMPACT: Part shared across {sibling_models_count} vehicle models.")

        # Determine Priority Tier
        if is_safety or evidence_state == ImplementationEvidenceState.CONFLICTING_EVIDENCE.value:
            priority = ReviewPriority.CRITICAL_P0.value
            requires_review = True
        elif (net_opportunity_inr and net_opportunity_inr >= cls.HIGH_VALUE_OPPORTUNITY_THRESHOLD_INR) or calibrated_confidence_score < 0.65:
            priority = ReviewPriority.HIGH_P1.value
            requires_review = True
        elif data_quality != DataQualityStatus.COMPLETE.value or sibling_models_count >= 3:
            priority = ReviewPriority.MEDIUM_P2.value
            requires_review = True
        elif reasons:
            priority = ReviewPriority.LOW_P3.value
            requires_review = True
        else:
            priority = ReviewPriority.LOW_P3.value
            requires_review = False

        return ReviewRoutingResult(
            requires_human_review=requires_review,
            review_priority=priority,
            is_safety_critical=is_safety,
            routing_reasons=reasons,
        )
