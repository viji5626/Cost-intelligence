"""
Deterministic Evidence Evaluation & Grounding Engine
Implements the 7-State Implementation Evidence Decision Logic, 8 distinct unmerged dimensions,
technical equivalence verification, versioned historical policies, conflict detection, and claim grounding.
"""

import re
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from ai.context.models import ContextItem, SourceAuthorityEnum
from ai.grounding.models import (
    ApplicabilityScopeEnum,
    ClassifiedEvidenceItem,
    EvidenceClassificationEnum,
    GroundingClaim,
    GroundingEvaluationResult,
    GroundingEvaluationSpec,
    HistoricalValidityPolicy,
    ImplementationDecisionEnum,
    ImplementationRelationshipEnum,
    TemporalValidityEnum,
)
from ai.retrieval.hybrid_engine import RetrievedDocument
from database.models.ideathon import ImplementationEvidenceState


class EvidenceEvaluator:
    """
    Evaluates retrieved evidence items against engineering claims and domain policies.
    Maintains strict mathematical separation across all 8 evaluation dimensions.
    """

    @classmethod
    def evaluate_temporal_validity(
        cls,
        item_date_str: Optional[str],
        submission_date: Optional[date],
        source_type: str,
        is_obsolete: bool,
        policy: HistoricalValidityPolicy,
    ) -> Tuple[TemporalValidityEnum, bool]:
        """
        Determines temporal status using configurable, versioned historical validity policy.
        Returns: (TemporalValidityEnum, is_historical)
        """
        if is_obsolete:
            return TemporalValidityEnum.HISTORICAL_SUPERSEDED, True

        if not item_date_str:
            return TemporalValidityEnum.TIME_UNKNOWN, False

        try:
            # Parse ISO date string (YYYY-MM-DD or YYYY)
            if len(item_date_str) == 4:
                item_dt = date(int(item_date_str), 1, 1)
            else:
                item_dt = datetime.strptime(item_date_str[:10], "%Y-%m-%d").date()
        except Exception:
            return TemporalValidityEnum.TIME_UNKNOWN, False

        ref_date = date.today()

        # Check future SOP
        if item_dt > ref_date:
            return TemporalValidityEnum.FUTURE_EFFECTIVE, False

        # Lifespan limit check from policy
        max_years = policy.max_active_lifespan_years.get(source_type, 5)
        age_years = (ref_date - item_dt).days / 365.25

        if age_years > max_years:
            return TemporalValidityEnum.HISTORICAL_SUPERSEDED, True

        # Check if submission_date explicitly provided and item is substantially older than submission
        if submission_date and (submission_date - item_dt).days > (max_years * 365.25):
            return TemporalValidityEnum.PREDATES_SUBMISSION, True

        return TemporalValidityEnum.CURRENT_ACTIVE, False

    @classmethod
    def evaluate_technical_equivalence(
        cls,
        target_problem: Optional[str],
        target_solution: Optional[str],
        evidence_text: str,
    ) -> ImplementationRelationshipEnum:
        """
        Evaluates whether evidence represents the SAME engineering change vs merely SIMILAR text.
        Example:
          - Idea: 'Change steel handlebar weight to aluminum'
          - Evidence: 'Reduce handlebar weight by geometry optimization' -> TECHNICAL_DIFFERENT
          - Evidence: 'Material substitution: Steel to Al alloy weight' -> DIRECT_CHANGE
        """
        d_lower = evidence_text.lower()
        sol_lower = (target_solution or target_problem or "").lower()

        # Check for contradictory / rejection claims in evidence
        if any(w in d_lower for w in ["cancelled", "rejected", "failed validation", "obsolete", "infeasible", "rolled back"]):
            return ImplementationRelationshipEnum.CONTRADICTORY_CLAIM

        if not sol_lower:
            return ImplementationRelationshipEnum.PARTIAL_EQUIVALENT

        # Check material substitution alignment
        material_pairs = [
            ("aluminum", "al alloy"), ("steel", "ci"), ("plastic", "polymer"),
            ("sheet metal", "tubular"), ("cast iron", "sg iron")
        ]
        has_material_intent = any(m1 in sol_lower or m2 in sol_lower for m1, m2 in material_pairs)
        if has_material_intent:
            # Check if evidence mentions material change or purely geometry/process
            if any(w in d_lower for w in ["material substitution", "alloy", "aluminum", "polymer", "composite", "grade", "al alloy"]):
                return ImplementationRelationshipEnum.DIRECT_CHANGE
            elif any(w in d_lower for w in ["geometry", "wall thickness", "rib optimization", "cavity"]):
                return ImplementationRelationshipEnum.TECHNICAL_DIFFERENT

        # Check process vs design change
        if "machining" in sol_lower and "casting" in d_lower and "machining" not in d_lower:
            return ImplementationRelationshipEnum.TECHNICAL_DIFFERENT

        # Check overlap of key technical nouns with stem/prefix matching
        sol_words = set(re.findall(r"\b[a-z]{3,}\b", sol_lower))
        doc_words = set(re.findall(r"\b[a-z]{3,}\b", d_lower))
        matched_count = 0
        for sw in sol_words:
            if any(sw == dw or (len(sw) >= 4 and len(dw) >= 4 and (sw.startswith(dw[:4]) or dw.startswith(sw[:4]))) for dw in doc_words):
                matched_count += 1

        ratio = matched_count / max(len(sol_words), 1)

        if ratio >= 0.50:
            return ImplementationRelationshipEnum.DIRECT_CHANGE
        elif ratio >= 0.25:
            return ImplementationRelationshipEnum.PARTIAL_EQUIVALENT
        else:
            return ImplementationRelationshipEnum.IRRELEVANT

    @classmethod
    def classify_evidence_item(
        cls,
        doc: RetrievedDocument,
        target_part_number: Optional[str],
        target_model_code: Optional[str],
        target_problem: Optional[str],
        target_solution: Optional[str],
        applicable_sibling_models: Optional[List[str]],
        submission_date: Optional[date],
        spec: GroundingEvaluationSpec,
    ) -> ClassifiedEvidenceItem:
        """
        Classifies an individual document across all 8 distinct dimensions.
        """
        sibling_models = applicable_sibling_models or []
        doc_meta = doc.metadata or {}
        source_type = doc_meta.get("source_type", doc.entity_type or "ECN").upper()
        doc_part = doc.part_number or doc_meta.get("part_number")
        doc_model = doc.model_code or doc_meta.get("model_code")
        effective_date = doc_meta.get("effective_date") or doc_meta.get("release_date")
        is_obsolete = doc_meta.get("is_obsolete", False) or doc_meta.get("status", "").upper() in ["OBSOLETE", "CANCELLED"]

        # Dimension 1: Retrieval Relevance (RRF score)
        dim1_retrieval = round(doc.score, 4)

        # Dimension 2: Reranker Relevance (Cross-encoder score)
        dim2_rerank = round(doc.rerank_score if doc.rerank_score is not None else doc.score, 4)

        # Dimension 3: Source Authority Hierarchy
        authority_class = doc_meta.get("authority_class")
        if isinstance(authority_class, str):
            try:
                auth_enum = SourceAuthorityEnum(authority_class)
            except Exception:
                auth_enum = SourceAuthorityEnum.SECONDARY_EXTERNAL
        elif isinstance(authority_class, SourceAuthorityEnum):
            auth_enum = authority_class
        else:
            if source_type in ["ECN", "ECR", "CERTIFIED_TEST"]:
                auth_enum = SourceAuthorityEnum.AUTHORITATIVE_ENGINEERING
            elif source_type in ["BOM", "PART_MASTER"]:
                auth_enum = SourceAuthorityEnum.BOM_MASTER_DATA
            elif source_type in ["PLANT_OPEX", "UTILITY"]:
                auth_enum = SourceAuthorityEnum.PLANT_OPEX_ACTUALS
            else:
                auth_enum = SourceAuthorityEnum.HISTORICAL_IMPLEMENTATION
        dim3_authority = auth_enum.weight

        # Dimension 4: Evidence Strength (Artifact Type)
        strength_weights = {
            "ECN": 0.95,
            "ECR": 0.85,
            "BOM": 0.90,
            "TEST_REPORT": 0.85,
            "PLANT_OPEX": 0.80,
            "HISTORICAL_PROJECT": 0.75,
            "IDEATHON": 0.40,
        }
        dim4_strength = strength_weights.get(source_type, 0.50)

        # Dimension 5: Applicability Scope & Part Isolation
        doc_ecn = doc_meta.get("code_or_number") or getattr(doc, "ecn_number", None)
        has_exact_ecn_match = False
        if doc_ecn and doc_ecn.upper() in (target_solution or target_problem or "").upper():
            has_exact_ecn_match = True

        has_part_mismatch = bool(target_part_number and doc_part and target_part_number != doc_part)

        if has_part_mismatch:
            dim5_app = ApplicabilityScopeEnum.NOT_APPLICABLE
        elif has_exact_ecn_match:
            dim5_app = ApplicabilityScopeEnum.EXACT_MODEL_MATCH
        elif target_part_number and doc_part == target_part_number:
            if not target_model_code or not doc_model or target_model_code.upper() in doc_model.upper():
                dim5_app = ApplicabilityScopeEnum.EXACT_MODEL_MATCH
            elif any(s.upper() in doc_model.upper() for s in sibling_models):
                dim5_app = ApplicabilityScopeEnum.CROSS_MODEL_APPLICABLE
            else:
                dim5_app = ApplicabilityScopeEnum.CROSS_MODEL_UNCONFIRMED
        elif target_model_code and doc_model and target_model_code.upper() in doc_model.upper():
            dim5_app = ApplicabilityScopeEnum.EXACT_MODEL_MATCH
        elif doc_model and any(s.upper() in doc_model.upper() for s in sibling_models):
            dim5_app = ApplicabilityScopeEnum.CROSS_MODEL_APPLICABLE
        elif doc_model:
            dim5_app = ApplicabilityScopeEnum.CROSS_MODEL_UNCONFIRMED
        elif not target_part_number and not target_model_code and source_type not in ["PLANT_OPEX", "UTILITY"]:
            dim5_app = ApplicabilityScopeEnum.CROSS_MODEL_UNCONFIRMED
        else:
            dim5_app = ApplicabilityScopeEnum.NOT_APPLICABLE

        # Dimension 6: Temporal Validity
        dim6_temp, is_historical = cls.evaluate_temporal_validity(
            item_date_str=effective_date,
            submission_date=submission_date,
            source_type=source_type,
            is_obsolete=is_obsolete,
            policy=spec.historical_policy,
        )

        # Dimension 7: Implementation Relationship (Technical Equivalence)
        if has_part_mismatch:
            dim7_rel = ImplementationRelationshipEnum.IRRELEVANT
        elif has_exact_ecn_match:
            dim7_rel = ImplementationRelationshipEnum.DIRECT_CHANGE
        else:
            effective_sol = target_solution or target_problem
            dim7_rel = cls.evaluate_technical_equivalence(
                target_problem=target_problem,
                target_solution=effective_sol,
                evidence_text=doc.text,
            )

        # Dimension 8: Grounding Contribution
        dim8_grounding = 0.0
        if dim7_rel == ImplementationRelationshipEnum.DIRECT_CHANGE and dim5_app != ApplicabilityScopeEnum.NOT_APPLICABLE:
            dim8_grounding = round(dim2_rerank * dim3_authority * dim4_strength, 4)
        elif dim7_rel == ImplementationRelationshipEnum.PARTIAL_EQUIVALENT and dim5_app != ApplicabilityScopeEnum.NOT_APPLICABLE:
            dim8_grounding = round(dim2_rerank * dim3_authority * dim4_strength * 0.60, 4)

        # Determine Classification
        status_upper = doc_meta.get("status", "").upper()
        is_conflicting = (
            dim7_rel == ImplementationRelationshipEnum.CONTRADICTORY_CLAIM
            or doc_meta.get("is_conflicting", False)
            or status_upper == "CONFLICTING"
        )

        if has_part_mismatch or dim7_rel == ImplementationRelationshipEnum.IRRELEVANT or dim5_app == ApplicabilityScopeEnum.NOT_APPLICABLE or dim2_rerank < 0.20:
            classification = EvidenceClassificationEnum.IRRELEVANT_EVIDENCE
        elif is_conflicting:
            classification = EvidenceClassificationEnum.CONFLICTING_EVIDENCE
        elif is_historical or dim6_temp == TemporalValidityEnum.HISTORICAL_SUPERSEDED:
            classification = EvidenceClassificationEnum.HISTORICAL_EVIDENCE
        elif dim7_rel == ImplementationRelationshipEnum.TECHNICAL_DIFFERENT:
            classification = EvidenceClassificationEnum.INDIRECT_EVIDENCE
        elif status_upper in ["DRAFT", "CONCEPT", "PENDING_REVIEW"] or dim4_strength < 0.50 or dim2_rerank < 0.45:
            classification = EvidenceClassificationEnum.INSUFFICIENT_EVIDENCE
        elif dim7_rel == ImplementationRelationshipEnum.DIRECT_CHANGE and dim4_strength >= 0.85 and dim5_app == ApplicabilityScopeEnum.EXACT_MODEL_MATCH:
            classification = EvidenceClassificationEnum.DIRECT_EVIDENCE
        elif dim4_strength >= 0.70 and dim5_app == ApplicabilityScopeEnum.CROSS_MODEL_APPLICABLE:
            classification = EvidenceClassificationEnum.SUPPORTING_EVIDENCE
        else:
            classification = EvidenceClassificationEnum.SUPPORTING_EVIDENCE

        return ClassifiedEvidenceItem(
            evidence_id=doc.id,
            source_id=doc.entity_id,
            source_type=source_type,
            code_or_number=doc_meta.get("code_or_number", doc.part_number or doc.id),
            title=doc_meta.get("title", doc.text[:60]),
            snippet=doc.text[:250],
            part_number=doc_part,
            model_code=doc_model,
            category=doc.category,
            dim1_retrieval_relevance=dim1_retrieval,
            dim2_reranker_relevance=dim2_rerank,
            dim3_source_authority=dim3_authority,
            dim4_evidence_strength=dim4_strength,
            dim5_applicability=dim5_app,
            dim6_temporal_validity=dim6_temp,
            dim7_implementation_relationship=dim7_rel,
            dim8_grounding_contribution=dim8_grounding,
            classification=classification,
            effective_date=effective_date,
            is_historical=is_historical,
            is_conflicting=is_conflicting,
            metadata=doc_meta,
        )

    @classmethod
    def evaluate_grounding_and_decision(
        cls,
        query_text: str,
        retrieved_docs: List[RetrievedDocument],
        target_part_number: Optional[str] = None,
        target_model_code: Optional[str] = None,
        target_problem: Optional[str] = None,
        target_solution: Optional[str] = None,
        applicable_sibling_models: Optional[List[str]] = None,
        submission_date: Optional[date] = None,
        spec: Optional[GroundingEvaluationSpec] = None,
        idea_id: Optional[str] = None,
    ) -> GroundingEvaluationResult:
        """
        Synthesizes classified evidence into one of the 7 deterministic states and computes grounding score.
        Enforces the sovereign business invariant: NO_EVIDENCE_FOUND != NOT_IMPLEMENTED.
        """
        from ai.grounding.models import FullRetrievalProvenance
        spec = spec or GroundingEvaluationSpec()
        sibling_models = applicable_sibling_models or []
        sub_date = submission_date or date.today()

        # 1. SCENARIO: Zero retrieved documents
        if not retrieved_docs:
            provenance = FullRetrievalProvenance(
                request_id=f"req-eval-{int(datetime.now(timezone.utc).timestamp())}",
                idea_id=idea_id,
                raw_query=query_text,
                extracted_identifiers={"part_number": target_part_number, "model_code": target_model_code},
                strategies_executed=["EXACT_IDENTIFIER", "KEYWORD_TRIGRAM", "DENSE_VECTOR"],
                candidates_retrieved_count=0,
                candidates_reranked_count=0,
                grounding_policy_version=spec.authority_policy_version,
                authority_policy_version=spec.authority_policy_version,
                historical_policy_version=spec.historical_policy.policy_version,
                stopping_reason="ZERO_CANDIDATES_RETURNED",
            )
            return GroundingEvaluationResult(
                request_id=provenance.request_id,
                idea_id=idea_id,
                query=query_text,
                decision=ImplementationDecisionEnum.NO_IMPLEMENTATION_EVIDENCE_FOUND,
                grounding_score=0.0,
                confidence_score=0.95,
                summary="No matching ECNs, BOM revisions, or plant implementation records discovered in corpus.",
                claims=[
                    GroundingClaim(
                        claim_id="claim-01",
                        claim_text=f"Implementation of {target_part_number or 'component'} on {target_model_code or 'vehicle'}",
                        is_supported=False,
                        certainty=0.0,
                        notes="No evidence found in search index.",
                    )
                ],
                classified_evidences=[],
                requires_human_review=False,
                review_reasons=[],
                provenance=provenance,
            )

        # 2. Classify all retrieved items
        eff_solution = target_solution or (query_text if not target_problem else None)
        classified_items: List[ClassifiedEvidenceItem] = []
        for doc in retrieved_docs:
            classified_items.append(
                cls.classify_evidence_item(
                    doc=doc,
                    target_part_number=target_part_number,
                    target_model_code=target_model_code,
                    target_problem=target_problem,
                    target_solution=eff_solution,
                    applicable_sibling_models=sibling_models,
                    submission_date=sub_date,
                    spec=spec,
                )
            )

        # Partition by classification
        direct_items = [c for c in classified_items if c.classification == EvidenceClassificationEnum.DIRECT_EVIDENCE]
        supporting_items = [c for c in classified_items if c.classification == EvidenceClassificationEnum.SUPPORTING_EVIDENCE]
        historical_items = [c for c in classified_items if c.classification == EvidenceClassificationEnum.HISTORICAL_EVIDENCE]
        conflicting_items = [c for c in classified_items if c.classification == EvidenceClassificationEnum.CONFLICTING_EVIDENCE]
        indirect_items = [c for c in classified_items if c.classification == EvidenceClassificationEnum.INDIRECT_EVIDENCE]
        insufficient_items = [c for c in classified_items if c.classification == EvidenceClassificationEnum.INSUFFICIENT_EVIDENCE]

        # Check for cross-record status conflicts
        statuses = set([c.metadata.get("status", "").upper() for c in classified_items if c.metadata.get("status")])
        has_cross_conflict = "RELEASED" in statuses and any(s in statuses for s in ["OBSOLETE", "CANCELLED", "REJECTED", "CONFLICTING"])

        # Calculate Grounding Score: Grounding contribution of verified direct/supporting evidence
        if direct_items:
            raw_grounding_score = round(max(c.dim8_grounding_contribution for c in direct_items), 4)
        elif supporting_items:
            raw_grounding_score = round(max(c.dim8_grounding_contribution for c in supporting_items), 4)
        else:
            raw_grounding_score = 0.0

        # Build Claims
        claims: List[GroundingClaim] = []
        claim_1_supported = len(direct_items) > 0 or (len(supporting_items) > 0 and raw_grounding_score >= 0.30)
        claim_1_evidence_ids = [c.evidence_id for c in (direct_items + supporting_items)[:3]]
        claims.append(
            GroundingClaim(
                claim_id="claim-01",
                claim_text=f"Engineering change for {target_part_number or 'component'} on {target_model_code or 'vehicle'}",
                is_supported=claim_1_supported,
                supporting_evidence_ids=claim_1_evidence_ids,
                certainty=round(raw_grounding_score, 2),
                notes="Verified via direct ECN/BOM closure" if claim_1_supported else "Unconfirmed or insufficient evidence",
            )
        )

        requires_review = False
        review_reasons: List[str] = []
        confirmed_models: List[str] = []
        unconfirmed_models: List[str] = []

        # Decision State Evaluation Matrix
        if conflicting_items or has_cross_conflict:
            decision = ImplementationDecisionEnum.CONFLICTING_EVIDENCE
            confidence = 0.70
            summary = "Contradictory implementation records discovered (e.g. active release vs cancellation/obsolescence)."
            requires_review = True
            review_reasons.append("Conflicting ECN lifecycle statuses or contradictory claims discovered.")

        elif all(c.classification == EvidenceClassificationEnum.IRRELEVANT_EVIDENCE for c in classified_items):
            decision = ImplementationDecisionEnum.NO_IMPLEMENTATION_EVIDENCE_FOUND
            confidence = 0.90
            summary = "No applicable implementation evidence discovered for target part or vehicle."

        elif direct_items:
            # Check model applicability rollout
            direct_models = set([c.model_code for c in direct_items if c.model_code])
            if target_model_code:
                has_target_model = any(
                    c.model_code and target_model_code.upper() in c.model_code.upper()
                    for c in direct_items
                ) or any(c.dim5_applicability == ApplicabilityScopeEnum.EXACT_MODEL_MATCH for c in direct_items)
            else:
                has_target_model = True

            confirmed_models = sorted(list(direct_models))
            unconfirmed_models = [m for m in sibling_models if m not in confirmed_models]

            if not has_target_model and any(c.dim5_applicability == ApplicabilityScopeEnum.CROSS_MODEL_APPLICABLE for c in direct_items):
                decision = ImplementationDecisionEnum.PARTIALLY_CONFIRMED
                confidence = 0.85
                summary = f"Implementation active on sibling model ({', '.join(confirmed_models)}), cross-model opportunity exists for target {target_model_code or ''}."
            elif unconfirmed_models and len(sibling_models) > 1:
                decision = ImplementationDecisionEnum.PARTIALLY_CONFIRMED
                confidence = 0.88
                summary = f"Implementation confirmed on {', '.join(confirmed_models)}, but unconfirmed on sibling models ({', '.join(unconfirmed_models)})."
            else:
                decision = ImplementationDecisionEnum.IMPLEMENTATION_CONFIRMED
                confidence = 0.95
                summary = f"Active engineering implementation confirmed via authoritative record {direct_items[0].code_or_number}."

        elif classified_items and classified_items[0].classification == EvidenceClassificationEnum.HISTORICAL_EVIDENCE:
            decision = ImplementationDecisionEnum.HISTORICAL_IMPLEMENTATION
            confidence = 0.90
            summary = f"Historical implementation discovered (record {classified_items[0].code_or_number} released {classified_items[0].effective_date or 'in prior period'})."

        elif supporting_items:
            if any(c.dim5_applicability == ApplicabilityScopeEnum.CROSS_MODEL_APPLICABLE for c in supporting_items):
                direct_models = set([c.model_code for c in supporting_items if c.model_code])
                confirmed_models = sorted(list(direct_models))
                unconfirmed_models = [m for m in sibling_models if m not in confirmed_models]
                decision = ImplementationDecisionEnum.PARTIALLY_CONFIRMED
                confidence = 0.85
                summary = f"Implementation active on sibling model ({', '.join(confirmed_models)}), cross-model opportunity exists for target."
            else:
                decision = ImplementationDecisionEnum.POTENTIAL_IMPLEMENTATION_EVIDENCE
                confidence = 0.70
                summary = f"Supporting implementation evidence discovered ({supporting_items[0].code_or_number})."
                requires_review = True
                review_reasons.append("Supporting evidence found but full direct ECN closure pending.")

        elif historical_items:
            decision = ImplementationDecisionEnum.HISTORICAL_IMPLEMENTATION
            confidence = 0.90
            summary = f"Historical implementation discovered (record {historical_items[0].code_or_number} released {historical_items[0].effective_date or 'in prior period'})."

        elif indirect_items:
            decision = ImplementationDecisionEnum.POTENTIAL_IMPLEMENTATION_EVIDENCE
            confidence = 0.60
            summary = "Related or potential implementation evidence found, but technical mechanism differs or is pending."
            requires_review = True
            review_reasons.append("Candidate evidence addresses similar goal via different technical mechanism.")

        elif insufficient_items:
            decision = ImplementationDecisionEnum.INSUFFICIENT_EVIDENCE
            confidence = 0.45
            summary = "Low-confidence or ambiguous search matches. Insufficient detail to confirm implementation."
            requires_review = True
            review_reasons.append("Low-confidence search matches (< 0.45 relevance).")

        else:
            decision = ImplementationDecisionEnum.NO_IMPLEMENTATION_EVIDENCE_FOUND
            confidence = 0.80
            summary = "No authoritative implementation evidence found across multi-tier hierarchy."

        provenance = FullRetrievalProvenance(
            request_id=f"req-eval-{int(datetime.now(timezone.utc).timestamp())}",
            idea_id=idea_id,
            raw_query=query_text,
            extracted_identifiers={"part_number": target_part_number, "model_code": target_model_code},
            strategies_executed=["EXACT_IDENTIFIER", "KEYWORD_TRIGRAM", "DENSE_VECTOR", "RRF_FUSION", "CROSS_ENCODER_RERANK"],
            candidates_retrieved_count=len(retrieved_docs),
            candidates_reranked_count=len(classified_items),
            grounding_policy_version=spec.authority_policy_version,
            authority_policy_version=spec.authority_policy_version,
            historical_policy_version=spec.historical_policy.policy_version,
            stopping_reason="NORMAL_COMPLETION",
        )

        return GroundingEvaluationResult(
            request_id=provenance.request_id,
            idea_id=idea_id,
            query=query_text,
            decision=decision,
            grounding_score=raw_grounding_score,
            confidence_score=confidence,
            summary=summary,
            claims=claims,
            classified_evidences=classified_items,
            applicable_models_count=len(sibling_models) or (1 if confirmed_models else 0),
            confirmed_models=confirmed_models,
            unconfirmed_models=unconfirmed_models,
            requires_human_review=requires_review,
            review_reasons=review_reasons,
            provenance=provenance,
        )
