"""
Unit Tests for Evidence Discovery Engine - All 10 Required Scenarios
"""

from datetime import date
import pytest
from backend.app.services.discovery.evidence_discovery_engine import (
    DiscoveredEvidenceItem,
    EvidenceDiscoveryEngine,
)
from database.models.ideathon import ImplementationEvidenceState


def test_scenario_1_implemented_on_same_model():
    """Scenario 1: Active ECN released and implemented on target model."""
    ev = DiscoveredEvidenceItem(
        evidence_type="ECN",
        source_id="ecn-101",
        code_or_number="ECN-2024-0010",
        title="Reduce wall thickness of 11100-KCC-900 by 0.7mm",
        status="RELEASED",
        release_date=date(2024, 6, 1),
        affected_part="11100-KCC-900",
        affected_model="SPLENDOR_PLUS",
        confidence=0.95,
    )

    result = EvidenceDiscoveryEngine.evaluate_implementation_evidence(
        target_part_number="11100-KCC-900",
        target_model_code="SPLENDOR_PLUS",
        submission_date=date(2024, 1, 15),
        retrieved_evidences=[ev],
        applicable_sibling_models=["SPLENDOR_PLUS"],
    )

    assert result.evidence_state == ImplementationEvidenceState.IMPLEMENTATION_CONFIRMED.value
    assert result.confidence_score >= 0.90
    assert "SPLENDOR_PLUS" in result.confirmed_models


def test_scenario_2_implemented_on_another_variant():
    """Scenario 2: Implemented on Disc variant but not Drum variant."""
    ev = DiscoveredEvidenceItem(
        evidence_type="ECN",
        source_id="ecn-102",
        code_or_number="ECN-2024-0012",
        title="Brake lever bracket redesign on Disc variant",
        status="RELEASED",
        release_date=date(2024, 6, 1),
        affected_part="53100-KTR-900",
        affected_model="SPLENDOR_PLUS_DISC",
        confidence=0.90,
    )

    result = EvidenceDiscoveryEngine.evaluate_implementation_evidence(
        target_part_number="53100-KTR-900",
        target_model_code="SPLENDOR_PLUS_DRUM",
        submission_date=date(2024, 1, 15),
        retrieved_evidences=[ev],
        applicable_sibling_models=["SPLENDOR_PLUS_DRUM", "SPLENDOR_PLUS_DISC"],
    )

    assert result.evidence_state == ImplementationEvidenceState.PARTIALLY_CONFIRMED.value
    assert "SPLENDOR_PLUS_DISC" in result.confirmed_models
    assert "SPLENDOR_PLUS_DRUM" in result.unconfirmed_models


def test_scenario_3_implemented_on_sibling_model():
    """Scenario 3: Implemented on HF Deluxe, applicable to Splendor Plus."""
    ev = DiscoveredEvidenceItem(
        evidence_type="ECN",
        source_id="ecn-103",
        code_or_number="ECN-2024-0015",
        title="Center stand snap fit clip deployment on HF Deluxe",
        status="RELEASED",
        release_date=date(2024, 5, 20),
        affected_part="50500-KTC-900",
        affected_model="HF_DELUXE",
        confidence=0.92,
    )

    result = EvidenceDiscoveryEngine.evaluate_implementation_evidence(
        target_part_number="50500-KTC-900",
        target_model_code="SPLENDOR_PLUS",
        submission_date=date(2024, 1, 15),
        retrieved_evidences=[ev],
        applicable_sibling_models=["SPLENDOR_PLUS", "HF_DELUXE"],
    )

    assert result.evidence_state == ImplementationEvidenceState.PARTIALLY_CONFIRMED.value
    assert "HF_DELUXE" in result.confirmed_models
    assert "SPLENDOR_PLUS" in result.unconfirmed_models


def test_scenario_4_historical_implementation():
    """Scenario 4: ECN released before idea submission date."""
    ev = DiscoveredEvidenceItem(
        evidence_type="ECN",
        source_id="ecn-104",
        code_or_number="ECN-2021-0089",
        title="Historical wall thickness reduction on cylinder head cover",
        status="RELEASED",
        release_date=date(2021, 8, 10),
        affected_part="11100-KCC-900",
        affected_model="SPLENDOR_PLUS",
        confidence=0.95,
    )

    result = EvidenceDiscoveryEngine.evaluate_implementation_evidence(
        target_part_number="11100-KCC-900",
        target_model_code="SPLENDOR_PLUS",
        submission_date=date(2024, 1, 15),  # Idea submitted in 2024, ECN from 2021
        retrieved_evidences=[ev],
    )

    assert result.evidence_state == ImplementationEvidenceState.HISTORICAL_IMPLEMENTATION.value


def test_scenario_5_partial_implementation():
    """Scenario 5: Part used in 3 sibling models, but ECN only rolled out to 1."""
    ev = DiscoveredEvidenceItem(
        evidence_type="ECN",
        source_id="ecn-105",
        code_or_number="ECN-2024-0025",
        title="Common fastener consolidation on Glamour",
        status="RELEASED",
        release_date=date(2024, 6, 10),
        affected_part="90111-187-000",
        affected_model="GLAMOUR",
        confidence=0.90,
    )

    result = EvidenceDiscoveryEngine.evaluate_implementation_evidence(
        target_part_number="90111-187-000",
        target_model_code="SPLENDOR_PLUS",
        submission_date=date(2024, 1, 15),
        retrieved_evidences=[ev],
        applicable_sibling_models=["SPLENDOR_PLUS", "GLAMOUR", "PASSION_PLUS"],
    )

    assert result.evidence_state == ImplementationEvidenceState.PARTIALLY_CONFIRMED.value
    assert len(result.unconfirmed_models) == 2


def test_scenario_6_similar_idea_but_technically_different_implementation():
    """Scenario 6: Similar wording candidate in draft state with partial match."""
    ev = DiscoveredEvidenceItem(
        evidence_type="ECN",
        source_id="ecn-106",
        code_or_number="ECN-2024-0033-DRAFT",
        title="Bolt tightening torque specification increase on cylinder head",
        status="DRAFT",
        affected_part="11100-KCC-900",
        affected_model="SPLENDOR_PLUS",
        confidence=0.55,
    )

    result = EvidenceDiscoveryEngine.evaluate_implementation_evidence(
        target_part_number="11100-KCC-900",
        target_model_code="SPLENDOR_PLUS",
        submission_date=date(2024, 1, 15),
        retrieved_evidences=[ev],
    )

    assert result.evidence_state == ImplementationEvidenceState.POTENTIAL_EVIDENCE.value
    assert result.requires_human_review is True


def test_scenario_7_conflicting_implementation_records():
    """Scenario 7: Contradictory ECN records (e.g. RELEASED vs CANCELLED/CONFLICTING)."""
    ev1 = DiscoveredEvidenceItem(
        evidence_type="ECN",
        source_id="ecn-107a",
        code_or_number="ECN-2024-0040",
        title="Polymer bushing change on rear brake pedal",
        status="RELEASED",
        release_date=date(2024, 4, 1),
        affected_part="46500-KTR-700",
        confidence=0.85,
    )
    ev2 = DiscoveredEvidenceItem(
        evidence_type="ECN",
        source_id="ecn-107b",
        code_or_number="ECN-2024-0040-REV",
        title="Polymer bushing cancelled due to NVH degradation",
        status="CANCELLED",
        is_conflicting=True,
        affected_part="46500-KTR-700",
        confidence=0.85,
    )

    result = EvidenceDiscoveryEngine.evaluate_implementation_evidence(
        target_part_number="46500-KTR-700",
        target_model_code="GLAMOUR",
        submission_date=date(2024, 1, 15),
        retrieved_evidences=[ev1, ev2],
    )

    assert result.evidence_state == ImplementationEvidenceState.CONFLICTING_EVIDENCE.value
    assert result.requires_human_review is True


def test_scenario_8_search_finds_nothing():
    """
    Scenario 8: Search finds zero matching records.
    CRITICAL TEST: Output must be NO_EVIDENCE_FOUND and NEVER NOT_IMPLEMENTED.
    """
    result = EvidenceDiscoveryEngine.evaluate_implementation_evidence(
        target_part_number="13111-087-000",
        target_model_code="SPLENDOR_PLUS",
        submission_date=date(2024, 1, 15),
        retrieved_evidences=[],
    )

    assert result.evidence_state == ImplementationEvidenceState.NO_EVIDENCE_FOUND.value
    assert result.evidence_state != "NOT_IMPLEMENTED"
    assert result.confidence_score >= 0.90


def test_scenario_9_search_finds_weak_low_confidence_evidence():
    """Scenario 9: Search returns very low confidence (< 0.45) candidate."""
    ev = DiscoveredEvidenceItem(
        evidence_type="ECN",
        source_id="ecn-109",
        code_or_number="ECN-GENERIC",
        title="Generic stamping optimization",
        status="IN_REVIEW",
        confidence=0.35,  # Very weak confidence
    )

    result = EvidenceDiscoveryEngine.evaluate_implementation_evidence(
        target_part_number=None,
        target_model_code=None,
        submission_date=date(2024, 1, 15),
        retrieved_evidences=[ev],
    )

    assert result.evidence_state == ImplementationEvidenceState.INSUFFICIENT_EVIDENCE.value
    assert result.requires_human_review is True


def test_scenario_10_current_vs_obsolete_implementation():
    """Scenario 10: ECN marked as OBSOLETE superseded by newer design."""
    ev = DiscoveredEvidenceItem(
        evidence_type="ECN",
        source_id="ecn-110",
        code_or_number="ECN-2022-0019",
        title="Old bracket redesign superseded by single piece casting",
        status="OBSOLETE",
        is_obsolete=True,
        release_date=date(2022, 3, 1),
        affected_part="50500-KTC-900",
        confidence=0.88,
    )

    result = EvidenceDiscoveryEngine.evaluate_implementation_evidence(
        target_part_number="50500-KTC-900",
        target_model_code="HF_DELUXE",
        submission_date=date(2024, 1, 15),
        retrieved_evidences=[ev],
    )

    assert result.evidence_state == ImplementationEvidenceState.HISTORICAL_IMPLEMENTATION.value
