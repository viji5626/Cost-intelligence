"""
Multi-Horizon Evidence Discovery and Implementation State Engine
Implements the 7-State Implementation Evidence Taxonomy:
- IMPLEMENTATION_CONFIRMED
- PARTIALLY_CONFIRMED
- HISTORICAL_IMPLEMENTATION
- POTENTIAL_EVIDENCE
- NO_EVIDENCE_FOUND
- INSUFFICIENT_EVIDENCE
- CONFLICTING_EVIDENCE

CRITICAL INVARIANT: 'NO_EVIDENCE_FOUND' is NEVER converted to 'NOT_IMPLEMENTED'.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional
from database.models.ideathon import ImplementationEvidenceState


@dataclass
class DiscoveredEvidenceItem:
    """An individual piece of discovered implementation evidence (ECN, BOM change, Drawing)."""

    evidence_type: str  # ECN, BOM_RECORD, IMPLEMENTATION_RECORD, HISTORICAL_DRAWING
    source_id: str
    code_or_number: str
    title: str
    status: str  # RELEASED, DRAFT, IN_REVIEW, OBSOLETE, CONFLICTING
    release_date: Optional[date] = None
    affected_part: Optional[str] = None
    affected_model: Optional[str] = None
    confidence: float = 0.8
    match_reason: str = ""
    is_conflicting: bool = False
    is_obsolete: bool = False


@dataclass
class EvidenceEvaluationResult:
    """The synthesized outcome of the multi-horizon evidence discovery pass."""

    evidence_state: str  # One of the 7 ImplementationEvidenceState values
    confidence_score: float
    summary: str
    discovered_evidences: List[DiscoveredEvidenceItem] = field(default_factory=list)
    applicable_models_count: int = 0
    confirmed_models: List[str] = field(default_factory=list)
    unconfirmed_models: List[str] = field(default_factory=list)
    requires_human_review: bool = False
    review_reasons: List[str] = field(default_factory=list)
    provenance_details: Dict[str, Any] = field(default_factory=dict)


class EvidenceDiscoveryEngine:
    """
    Deterministic rule engine that synthesizes retrieved ECNs, BOM history,
    and cross-model sharing into an authoritative ImplementationEvidenceState.
    """

    @classmethod
    def evaluate_implementation_evidence(
        cls,
        target_part_number: Optional[str],
        target_model_code: Optional[str],
        submission_date: Optional[date],
        retrieved_evidences: List[DiscoveredEvidenceItem],
        applicable_sibling_models: Optional[List[str]] = None,
    ) -> EvidenceEvaluationResult:
        """
        Synthesizes discovered evidence items into one of the 7 deterministic states.
        """
        applicable_sibling_models = applicable_sibling_models or []
        sub_date = submission_date or date.today()

        # 1. Scenario: Search finds nothing at all
        if not retrieved_evidences:
            return EvidenceEvaluationResult(
                evidence_state=ImplementationEvidenceState.NO_EVIDENCE_FOUND.value,
                confidence_score=0.95,
                summary="No matching ECNs, BOM revisions, or historical implementation records discovered across multi-tier hierarchy.",
                discovered_evidences=[],
                requires_human_review=False,
                review_reasons=[],
                provenance_details={"search_hits": 0, "rule": "ZERO_DISCOVERED_EVIDENCE"},
            )

        # Filter active vs conflicting vs obsolete evidences
        released_exact_ecns: List[DiscoveredEvidenceItem] = []
        released_sibling_ecns: List[DiscoveredEvidenceItem] = []
        historical_ecns: List[DiscoveredEvidenceItem] = []
        conflicting_ecns: List[DiscoveredEvidenceItem] = []
        weak_candidates: List[DiscoveredEvidenceItem] = []

        has_status_conflict = False
        statuses_seen = set()

        for ev in retrieved_evidences:
            statuses_seen.add(ev.status.upper())
            if ev.is_conflicting:
                conflicting_ecns.append(ev)
                has_status_conflict = True
                continue

            # Check if historical (predates submission date or marked OBSOLETE/HISTORICAL)
            is_historical = ev.is_obsolete or (ev.release_date and ev.release_date < sub_date)

            if ev.confidence < 0.60:
                weak_candidates.append(ev)
            elif is_historical:
                historical_ecns.append(ev)
            elif ev.status.upper() in ["RELEASED", "IMPLEMENTED", "ACTIVE"]:
                # Check model alignment
                if target_model_code and ev.affected_model and target_model_code.upper() in ev.affected_model.upper():
                    released_exact_ecns.append(ev)
                elif ev.affected_model and any(s.upper() in ev.affected_model.upper() for s in applicable_sibling_models):
                    released_sibling_ecns.append(ev)
                elif not ev.affected_model or (target_part_number and ev.affected_part == target_part_number):
                    released_exact_ecns.append(ev)
                else:
                    weak_candidates.append(ev)
            else:
                weak_candidates.append(ev)

        # Check for explicit status conflict (e.g. RELEASED + CANCELLED/OBSOLETE for same change)
        if "RELEASED" in statuses_seen and any(s in statuses_seen for s in ["OBSOLETE", "CANCELLED", "REJECTED", "CONFLICTING"]):
            has_status_conflict = True

        # 2. Scenario: Conflicting Evidence
        if has_status_conflict or conflicting_ecns:
            return EvidenceEvaluationResult(
                evidence_state=ImplementationEvidenceState.CONFLICTING_EVIDENCE.value,
                confidence_score=0.65,
                summary="Conflicting implementation records discovered (e.g., contradictory release vs obsolescence status).",
                discovered_evidences=retrieved_evidences,
                requires_human_review=True,
                review_reasons=["Contradictory ECN lifecycle statuses detected across plant records."],
                provenance_details={"conflict_detected": True, "statuses": list(statuses_seen)},
            )

        # 3. Scenario: Exact Implementation Confirmed on target model
        if released_exact_ecns:
            confirmed_models = list(set([ev.affected_model for ev in released_exact_ecns if ev.affected_model]))
            if not confirmed_models and target_model_code:
                confirmed_models = [target_model_code]

            unconfirmed = [m for m in applicable_sibling_models if m not in confirmed_models]

            # If applicable to 3 models but only released on 1, it's partially confirmed
            if unconfirmed and len(applicable_sibling_models) > 1:
                return EvidenceEvaluationResult(
                    evidence_state=ImplementationEvidenceState.PARTIALLY_CONFIRMED.value,
                    confidence_score=0.88,
                    summary=f"Implementation confirmed on {', '.join(confirmed_models)}, but unconfirmed on sibling models ({', '.join(unconfirmed)}).",
                    discovered_evidences=retrieved_evidences,
                    applicable_models_count=len(applicable_sibling_models),
                    confirmed_models=confirmed_models,
                    unconfirmed_models=unconfirmed,
                    requires_human_review=False,
                    review_reasons=[],
                    provenance_details={"rule": "PARTIAL_PORTFOLIO_ROLLOUT", "confirmed": confirmed_models},
                )

            return EvidenceEvaluationResult(
                evidence_state=ImplementationEvidenceState.IMPLEMENTATION_CONFIRMED.value,
                confidence_score=0.95,
                summary=f"Active production implementation confirmed via ECN {released_exact_ecns[0].code_or_number}.",
                discovered_evidences=retrieved_evidences,
                applicable_models_count=len(applicable_sibling_models) or 1,
                confirmed_models=confirmed_models or [target_model_code or "ALL"],
                unconfirmed_models=[],
                requires_human_review=False,
                review_reasons=[],
                provenance_details={"rule": "EXACT_ACTIVE_ECN_MATCH", "ecn": released_exact_ecns[0].code_or_number},
            )

        # 4. Scenario: Implemented on Sibling Model / Variant Only
        if released_sibling_ecns:
            confirmed_models = list(set([ev.affected_model for ev in released_sibling_ecns if ev.affected_model]))
            unconfirmed = [m for m in applicable_sibling_models if m not in confirmed_models]
            return EvidenceEvaluationResult(
                evidence_state=ImplementationEvidenceState.PARTIALLY_CONFIRMED.value,
                confidence_score=0.85,
                summary=f"Implemented on sibling model ({', '.join(confirmed_models)}), cross-model opportunity exists for target {target_model_code}.",
                discovered_evidences=retrieved_evidences,
                applicable_models_count=len(applicable_sibling_models),
                confirmed_models=confirmed_models,
                unconfirmed_models=unconfirmed,
                requires_human_review=False,
                review_reasons=[],
                provenance_details={"rule": "SIBLING_MODEL_IMPLEMENTATION", "sibling_ecns": len(released_sibling_ecns)},
            )

        # 5. Scenario: Historical Implementation
        if historical_ecns:
            return EvidenceEvaluationResult(
                evidence_state=ImplementationEvidenceState.HISTORICAL_IMPLEMENTATION.value,
                confidence_score=0.90,
                summary=f"Historical implementation discovered (ECN {historical_ecns[0].code_or_number} released {historical_ecns[0].release_date}).",
                discovered_evidences=retrieved_evidences,
                requires_human_review=False,
                review_reasons=[],
                provenance_details={"rule": "HISTORICAL_ECN_PREDATES_IDEA", "ecn": historical_ecns[0].code_or_number},
            )

        # 6. Scenario: Weak or Low-Confidence Evidence
        if weak_candidates:
            # Check if confidence is extremely low
            if all(w.confidence < 0.45 for w in weak_candidates):
                return EvidenceEvaluationResult(
                    evidence_state=ImplementationEvidenceState.INSUFFICIENT_EVIDENCE.value,
                    confidence_score=0.40,
                    summary="Low-confidence or ambiguous change records discovered. Insufficient detail to confirm status.",
                    discovered_evidences=retrieved_evidences,
                    requires_human_review=True,
                    review_reasons=["Candidate ECNs matched with low confidence (< 0.45)."],
                    provenance_details={"rule": "LOW_CONFIDENCE_MATCH"},
                )

            return EvidenceEvaluationResult(
                evidence_state=ImplementationEvidenceState.POTENTIAL_EVIDENCE.value,
                confidence_score=0.60,
                summary="Potential implementation evidence identified in pending/draft ECNs.",
                discovered_evidences=retrieved_evidences,
                requires_human_review=True,
                review_reasons=["Candidate ECNs are in draft or pending review state."],
                provenance_details={"rule": "PENDING_OR_PARTIAL_MATCH"},
            )

        # Default fallback
        return EvidenceEvaluationResult(
            evidence_state=ImplementationEvidenceState.NO_EVIDENCE_FOUND.value,
            confidence_score=0.80,
            summary="No authoritative implementation evidence found.",
            discovered_evidences=retrieved_evidences,
            requires_human_review=False,
            provenance_details={"rule": "DEFAULT_NO_EVIDENCE"},
        )
