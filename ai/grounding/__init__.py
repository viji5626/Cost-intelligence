"""
AI Grounding & Evidence Evaluation Package
Integrates hybrid search, real cross-encoder reranking, context budgeting, and deterministic evidence evaluation.
"""

from ai.grounding.benchmark import BenchmarkScenario, GroundingBenchmarkSuite, MetricReport
from ai.grounding.evidence_evaluator import EvidenceEvaluator
from ai.grounding.models import (
    ApplicabilityScopeEnum,
    ClassifiedEvidenceItem,
    EvidenceClassificationEnum,
    FullRetrievalProvenance,
    GroundingClaim,
    GroundingEvaluationResult,
    GroundingEvaluationSpec,
    HistoricalValidityPolicy,
    ImplementationDecisionEnum,
    ImplementationRelationshipEnum,
    TemporalValidityEnum,
)
from ai.grounding.query_formulator import FormulatedQuery, QueryFormulator
from ai.grounding.retrieval_grounding_orchestrator import (
    RetrievalGroundingOrchestrator,
    grounding_orchestrator,
)

__all__ = [
    "ApplicabilityScopeEnum",
    "BenchmarkScenario",
    "ClassifiedEvidenceItem",
    "EvidenceClassificationEnum",
    "EvidenceEvaluator",
    "FormulatedQuery",
    "FullRetrievalProvenance",
    "GroundingBenchmarkSuite",
    "GroundingClaim",
    "GroundingEvaluationResult",
    "GroundingEvaluationSpec",
    "HistoricalValidityPolicy",
    "ImplementationDecisionEnum",
    "ImplementationRelationshipEnum",
    "MetricReport",
    "QueryFormulator",
    "RetrievalGroundingOrchestrator",
    "TemporalValidityEnum",
    "grounding_orchestrator",
]
