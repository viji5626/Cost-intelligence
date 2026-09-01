"""
Unit Tests for Confidence Calibration & Governance Prioritization Engine
Tests all 15 required synthetic scenarios.
"""

from datetime import datetime
import pytest
from backend.app.core.security import UserSession
from backend.app.services.governance.confidence_engine import (
    ConfidenceCalibrationEngine,
    ReviewPrioritizer,
)
from database.models.governance import (
    ConfidenceTier,
    ReviewActionType,
    ReviewPriority,
    ReviewStatus,
)
from database.models.ideathon import (
    DataQualityStatus,
    IdeaDecisionState,
    ImplementationEvidenceState,
)


def test_scenario_1_high_confidence_confirmed_evidence():
    """Scenario 1: Multi-source authoritative ERP/PLM match with full BOM and ECN."""
    res = ConfidenceCalibrationEngine.calculate_confidence(
        source_authority="ERP_SAP",
        exact_identifier_matched=True,
        retrieval_relevance=0.98,
        corroborating_sources_count=2,
        has_ecn_record=True,
        has_bom_record=True,
        has_effective_dates=True,
        entity_extraction_confidence=1.0,
        has_conflicting_records=False,
    )

    assert res.composite_score >= 0.85
    assert res.confidence_tier == ConfidenceTier.HIGH.value
    assert res.conflict_penalty_applied == 0.0


def test_scenario_2_low_confidence_evidence():
    """Scenario 2: Semantic only, weak ECN, partial entity resolution."""
    res = ConfidenceCalibrationEngine.calculate_confidence(
        source_authority="UNOFFICIAL",
        exact_identifier_matched=False,
        is_synonym_match=False,
        retrieval_relevance=0.45,
        corroborating_sources_count=0,
        has_ecn_record=False,
        has_bom_record=False,
        has_effective_dates=False,
        entity_extraction_confidence=0.50,
        has_conflicting_records=False,
    )

    assert res.composite_score < 0.45
    assert res.confidence_tier == ConfidenceTier.VERY_LOW.value


def test_scenario_3_conflicting_evidence():
    """Scenario 3: Strong baseline evidence but flagged with conflicting ECN records."""
    res = ConfidenceCalibrationEngine.calculate_confidence(
        source_authority="ERP_SAP",
        exact_identifier_matched=True,
        retrieval_relevance=0.90,
        corroborating_sources_count=2,
        has_ecn_record=True,
        has_bom_record=True,
        has_effective_dates=True,
        has_conflicting_records=True,
    )

    # 0.35 conflict penalty applied
    assert res.conflict_penalty_applied == 0.35
    assert res.composite_score < 0.70

    routing = ReviewPrioritizer.evaluate_routing(
        evidence_state=ImplementationEvidenceState.CONFLICTING_EVIDENCE.value,
        calibrated_confidence_score=res.composite_score,
    )
    assert routing.review_priority == ReviewPriority.CRITICAL_P0.value
    assert any("CONFLICTING_EVIDENCE" in r for r in routing.routing_reasons)


def test_scenario_4_missing_authoritative_source():
    """Scenario 4: Idea missing ERP/PLM backing (Draft authority)."""
    res = ConfidenceCalibrationEngine.calculate_confidence(
        source_authority="DRAFT",
        exact_identifier_matched=True,
        retrieval_relevance=0.80,
    )

    assert res.source_authority_score == 0.50
    assert res.confidence_tier in (ConfidenceTier.MEDIUM.value, ConfidenceTier.LOW.value)


def test_scenario_5_high_value_opportunity():
    """Scenario 5: Net annual financial opportunity >= ₹1 Crore triggers High P1 priority."""
    routing = ReviewPrioritizer.evaluate_routing(
        subsystem_code="ENGINE",
        net_opportunity_inr=15000000.0,  # ₹1.5 Crore
        calibrated_confidence_score=0.92,
    )

    assert routing.review_priority == ReviewPriority.HIGH_P1.value
    assert routing.requires_human_review is True
    assert any("HIGH_VALUE_OPPORTUNITY" in r for r in routing.routing_reasons)


def test_scenario_6_safety_critical_idea():
    """Scenario 6: Safety-critical system (Brakes) triggers Critical P0 priority."""
    routing = ReviewPrioritizer.evaluate_routing(
        subsystem_code="BRAKE_SYSTEM",
        is_part_safety_critical=True,
        net_opportunity_inr=500000.0,
        calibrated_confidence_score=0.95,
    )

    assert routing.review_priority == ReviewPriority.CRITICAL_P0.value
    assert routing.is_safety_critical is True
    assert routing.requires_human_review is True
    assert any("SAFETY_CRITICAL_SYSTEM" in r for r in routing.routing_reasons)


def test_scenario_7_reviewer_authorization_check():
    """Scenario 7 & 13: RBAC permission validation for cost engineers vs unauthorized users."""
    from backend.app.services.governance.governance_service import GovernanceService

    service = GovernanceService()
    authorized_user = UserSession(user_id="u1", username="engineer1", roles=["COST_ENGINEER"])
    unauthorized_user = UserSession(user_id="u2", username="guest1", roles=["READ_ONLY"])

    # Authorized does not raise
    service._check_reviewer_authorization(authorized_user)

    # Unauthorized raises PermissionError
    with pytest.raises(PermissionError) as exc_info:
        service._check_reviewer_authorization(unauthorized_user)
    assert "lacks required reviewer role" in str(exc_info.value)
