"""
Integration Tests for Executive AI Copilot API (/api/v1/executive-copilot/query)
Validates automatic backend persona resolution, zero-hallucination grounded queries, and deterministic truth invariants.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_copilot_auto_resolves_ceo_persona_from_dashboard_context():
    """Verifies backend automatically resolves CEO presentation policy when user is on Executive Dashboard."""
    payload = {
        "query": "What is our total annual cost reduction opportunity across plants?",
        "page_context": {"page": "EXECUTIVE_DASHBOARD"},
    }
    response = client.post("/api/v1/executive-copilot/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["persona_applied"] == "CEO"
    assert "Executive Overview scope" in data["persona_resolution_reason"]
    assert data["evidence_state"] == "VERIFIED"
    assert "₹" in data["answer"] or "Cr" in data["answer"]
    assert len(data["summary_points"]) >= 2
    assert len(data["citations"]) >= 1
    assert data["audit_hash"].startswith("sha256:")


def test_copilot_auto_resolves_plant_head_persona_from_opex_context():
    """Verifies backend automatically resolves PLANT_HEAD presentation policy from OPEX workspace context."""
    payload = {
        "query": "Why is Haridwar OPEX higher than Dharuhera?",
        "page_context": {"page": "OPEX_BENCHMARK", "plant_id": "HARIDWAR"},
    }
    response = client.post("/api/v1/executive-copilot/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["persona_applied"] == "PLANT_HEAD"
    assert "OPEX" in data["persona_resolution_reason"]
    assert "Haridwar" in data["answer"]
    assert "Dharuhera" in data["answer"]
    assert data["verified_metrics"]["benchmark_gap_per_vehicle_inr"] == 27.0
    assert "controllable_variance_pct" in data["verified_metrics"]


def test_copilot_auto_resolves_purchase_persona_from_sourcing_context():
    """Verifies backend automatically resolves PURCHASE presentation policy from purchase/sourcing context."""
    payload = {
        "query": "Which component cost outliers should sourcing investigate?",
        "page_context": {"page": "PURCHASE"},
    }
    response = client.post("/api/v1/executive-copilot/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["persona_applied"] == "PURCHASE"
    assert "51400-KCC-900" in str(data["verified_metrics"])
    assert data["verified_metrics"]["variance_per_unit_inr"] == 55.0


def test_copilot_auto_resolves_persona_from_rbac_headers():
    """Verifies backend resolves presentation policy from authenticated HTTP RBAC headers."""
    payload = {
        "query": "What is our cost summary?",
    }
    headers = {"X-User-Role": "PLANT_OPERATIONS_HEAD", "X-User-Department": "HARIDWAR_PLANT"}
    response = client.post("/api/v1/executive-copilot/query", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["persona_applied"] == "PLANT_HEAD"
    assert "Plant Operations role" in data["persona_resolution_reason"]


def test_copilot_query_ideathon_no_implementation_evidence_invariant():
    """
    CRITICAL INVARIANT:
    Verifies that NO_IMPLEMENTATION_EVIDENCE_FOUND is strictly returned and NEVER rendered as NOT_IMPLEMENTED.
    """
    payload = {
        "query": "Is Idea IDEA-0042 already implemented in production?",
        "page_context": {"page": "IDEATHON_PIPELINE"},
    }
    response = client.post("/api/v1/executive-copilot/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["persona_applied"] == "VAVE_COMMERCIAL"
    assert data["evidence_state"] == "NO_IMPLEMENTATION_EVIDENCE_FOUND"
    assert "NOT_IMPLEMENTED" not in data["answer"]
    assert "NO IMPLEMENTATION EVIDENCE FOUND" in data["answer"]
    assert data["verified_metrics"]["unit_saving_inr"] == 14.50


def test_copilot_query_safety_critical_p0():
    """Verifies safety-critical components (brakes/steering) enforce CRITICAL_P0 and block autonomous approvals."""
    payload = {
        "query": "Why are brake proposals flagged in safety review queue?",
        "page_context": {"page": "HUMAN_SAFETY_GATE"},
    }
    response = client.post("/api/v1/executive-copilot/query", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["persona_applied"] == "VAVE_COMMERCIAL"
    assert data["verified_metrics"]["safety_classification"] == "CRITICAL_P0"
    assert data["verified_metrics"]["autonomous_approval_allowed"] is False
    assert data["verified_metrics"]["mandatory_human_review"] is True


def test_copilot_empty_query_rejected():
    """Verifies empty query returns HTTP 400."""
    payload = {
        "query": "   ",
    }
    response = client.post("/api/v1/executive-copilot/query", json=payload)
    assert response.status_code == 400
