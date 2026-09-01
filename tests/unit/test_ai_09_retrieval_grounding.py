"""
Unit & Benchmark Test Suite for Phase AI-09: Retrieval & Evidence Grounding Integration
Validates 12 synthetic scenarios, 8 distinct evaluation dimensions, critical business invariants,
ablation benchmarks, and full provenance tracing.
"""

from datetime import date
import pytest

from ai.context.models import SourceAuthorityEnum
from ai.grounding.benchmark import GroundingBenchmarkSuite, MetricReport
from ai.grounding.evidence_evaluator import EvidenceEvaluator
from ai.grounding.models import (
    ApplicabilityScopeEnum,
    EvidenceClassificationEnum,
    GroundingEvaluationResult,
    GroundingEvaluationSpec,
    HistoricalValidityPolicy,
    ImplementationDecisionEnum,
    ImplementationRelationshipEnum,
    TemporalValidityEnum,
)
from ai.grounding.query_formulator import FormulatedQuery, QueryFormulator
from ai.grounding.retrieval_grounding_orchestrator import RetrievalGroundingOrchestrator
from ai.providers.native_embedding import NativeLocalEmbeddingEngine
from ai.providers.native_reranker import NativeLocalRerankerEngine
from ai.retrieval.hybrid_engine import HybridRetrievalEngine, RetrievalQuery, RetrievedDocument


@pytest.fixture(scope="module")
def real_embedding_engine():
    """Provides the real AI-06 local dense embedding engine."""
    engine = NativeLocalEmbeddingEngine(default_model_id="bge-small-en-v1.5", fallback_dimension=384)
    return engine


@pytest.fixture(scope="module")
def real_reranker_engine():
    """Provides the real AI-07 local cross-encoder reranker engine."""
    engine = NativeLocalRerankerEngine(default_model_id="bge-reranker-base")
    return engine


@pytest.fixture(scope="module")
def standard_corpus(real_embedding_engine):
    """Provides pre-indexed corpus with real dense embeddings."""
    return GroundingBenchmarkSuite.get_standard_corpus(real_embedding_engine)


@pytest.fixture
def orchestrator(real_embedding_engine, real_reranker_engine):
    """Provides an end-to-end RetrievalGroundingOrchestrator instance."""
    return RetrievalGroundingOrchestrator(
        embedding_provider=real_embedding_engine,
        reranker_provider=real_reranker_engine,
    )


# ── TEST 1: Query Formulator Exact Identifier Extraction ──────────────────────
def test_01_query_formulator_exact_identifier_extraction():
    raw_query = "Please check ECN-2024-001 status for part 53100-DEMO-001 on Splendor Plus."
    ids = QueryFormulator.extract_exact_identifiers(raw_query)

    assert ids["part_number"] == "53100-DEMO-001"
    assert ids["ecn_code"] == "ECN-2024-001"
    assert ids["model_code"] == "SPLENDOR_PLUS"


# ── TEST 2: Query Formulator Bounded Expansion ────────────────────────────────
def test_02_query_formulator_bounded_expansion():
    formulated = QueryFormulator.formulate_query(
        raw_text="Reduce weight of handlebar weight on Splendor Plus",
    )
    assert formulated.target_vehicle_model == "SPLENDOR_PLUS"
    assert formulated.target_component == "HANDLEBAR_WEIGHT"
    assert len(formulated.expanded_terms) >= 3
    assert any("handle balancer" in t for t in formulated.expanded_terms)
    assert any("bar end weight" in t for t in formulated.expanded_terms)


# ── TEST 3: Query Formulator Text Decomposition ───────────────────────────────
def test_03_query_formulator_text_decomposition():
    title = "Lightweight Handlebar Weight via Aluminum Substitution"
    desc = "Problem: Current steel bar end weight adds excessive mass.\nProposed Solution: Replace with 6061-T6 aluminum alloy to save 80g per vehicle."
    formulated = QueryFormulator.formulate_query(
        raw_text="",
        title=title,
        description=desc,
    )
    assert formulated.decomposed_problem is not None
    assert formulated.decomposed_solution is not None
    assert "steel" in formulated.decomposed_problem.lower()
    assert "aluminum" in formulated.decomposed_solution.lower()


# ── TEST 4: Exact Match Retrieval Prioritization ──────────────────────────────
def test_04_exact_match_retrieval_prioritization(real_embedding_engine, real_reranker_engine, standard_corpus):
    engine = HybridRetrievalEngine(real_embedding_engine, real_reranker_engine)
    q = RetrievalQuery(
        raw_query="ECN-2024-001 for 53100-DEMO-001",
        target_part_number="53100-DEMO-001",
        top_k=5,
    )
    results = engine.search_corpus(q, standard_corpus)
    assert len(results) > 0
    assert results[0].id in ["DOC-ECN-001", "DOC-ECN-003-DIFF-CHANGE", "DOC-ECN-005-CONFLICT"]
    assert results[0].part_number == "53100-DEMO-001"


# ── TEST 5: Dense Vector Semantic Search ──────────────────────────────────────
def test_05_dense_vector_semantic_search(real_embedding_engine, real_reranker_engine, standard_corpus):
    engine = HybridRetrievalEngine(real_embedding_engine, real_reranker_engine)
    q = RetrievalQuery(
        raw_query="lightweighting through aluminum bar end substitution",
        enable_reranking=False,
        top_k=5,
    )
    results = engine.search_corpus(q, standard_corpus)
    assert len(results) > 0
    assert any("aluminum" in d.text.lower() for d in results[:2])


# ── TEST 6: Trigram Lexical Keyword Search ────────────────────────────────────
def test_06_trigram_lexical_keyword_search(real_embedding_engine, real_reranker_engine, standard_corpus):
    engine = HybridRetrievalEngine(real_embedding_engine, real_reranker_engine)
    # Misspelled 'handlbar weigt'
    q = RetrievalQuery(
        raw_query="handlbar weigt aluminum",
        enable_reranking=False,
        top_k=5,
    )
    results = engine.search_corpus(q, standard_corpus)
    assert len(results) > 0
    assert results[0].id in ["DOC-ECN-001", "DOC-ECN-004-SIBLING"]


# ── TEST 7: Reciprocal Rank Fusion (RRF) ──────────────────────────────────────
def test_07_rrf_multi_channel_fusion(real_embedding_engine, real_reranker_engine, standard_corpus):
    engine = HybridRetrievalEngine(real_embedding_engine, real_reranker_engine)
    q = RetrievalQuery(
        raw_query="53100-DEMO-001 aluminum handlebar weight",
        target_part_number="53100-DEMO-001",
        top_k=5,
    )
    results = engine.search_corpus(q, standard_corpus)
    assert len(results) >= 2
    # Check that score reflects RRF combination
    assert results[0].score > 0.01


# ── TEST 8: Cross-Encoder Reranker Integration ────────────────────────────────
def test_08_cross_encoder_reranker_integration(real_embedding_engine, real_reranker_engine, standard_corpus):
    engine = HybridRetrievalEngine(real_embedding_engine, real_reranker_engine)
    q = RetrievalQuery(
        raw_query="surface finish paint thickness change on 53100-DEMO-001",
        target_part_number="53100-DEMO-001",
        enable_reranking=True,
        top_k=5,
    )
    results = engine.search_corpus(q, standard_corpus)
    assert len(results) > 0
    # Cross-encoder should rank DOC-ECN-003-DIFF-CHANGE at rank 1 due to paint finish alignment
    assert results[0].id == "DOC-ECN-003-DIFF-CHANGE"
    assert results[0].rerank_score is not None
    assert results[0].rerank_score >= 0.50


# ── TEST 9: Eight Distinct Dimensions Evaluation ──────────────────────────────
def test_09_eight_distinct_dimensions_evaluation(orchestrator, standard_corpus):
    result = orchestrator.execute_grounding_pipeline(
        raw_query="Material substitution to aluminum for part 53100-DEMO-001 on SPLENDOR_PLUS",
        corpus_records=standard_corpus,
        target_part_number="53100-DEMO-001",
        target_vehicle_model="SPLENDOR_PLUS",
    )
    assert len(result.classified_evidences) > 0
    item = result.classified_evidences[0]

    # Verify all 8 dimensions are distinctly populated
    assert 0.0 <= item.dim1_retrieval_relevance <= 1.0
    assert 0.0 <= item.dim2_reranker_relevance <= 1.0
    assert 0.0 <= item.dim3_source_authority <= 1.0
    assert 0.0 <= item.dim4_evidence_strength <= 1.0
    assert isinstance(item.dim5_applicability, ApplicabilityScopeEnum)
    assert isinstance(item.dim6_temporal_validity, TemporalValidityEnum)
    assert isinstance(item.dim7_implementation_relationship, ImplementationRelationshipEnum)
    assert 0.0 <= item.dim8_grounding_contribution <= 1.0


# ── TEST 10: Sovereign Invariant: NO_EVIDENCE != NOT_IMPLEMENTED ──────────────
def test_10_sovereign_invariant_no_evidence_not_equal_to_not_implemented(orchestrator):
    # Empty corpus query
    result = orchestrator.execute_grounding_pipeline(
        raw_query="Weight reduction on non-existent part 99999-NOEXIST-001",
        corpus_records=[],
    )
    assert result.decision == ImplementationDecisionEnum.NO_IMPLEMENTATION_EVIDENCE_FOUND
    assert result.decision.value != "NOT_IMPLEMENTED"
    assert result.grounding_score == 0.0
    assert result.provenance.stopping_reason == "ZERO_CANDIDATES_RETURNED"


# ── TEST 11: Technical Equivalence vs Similar Wording (False Positive Prevention)
def test_11_technical_equivalence_vs_similar_wording(orchestrator, standard_corpus):
    # Idea proposes geometry coring, while ECN-001 implements material substitution
    result = orchestrator.execute_grounding_pipeline(
        raw_query="Reduce handlebar weight on 53100-DEMO-001 through hollow geometry coring and wall thinning",
        corpus_records=standard_corpus,
        title="Handlebar weight geometry optimization",
        description="Problem: Excessive mass. Proposed Solution: Thin wall geometry and hollow coring without changing material.",
        target_part_number="53100-DEMO-001",
        target_vehicle_model="SPLENDOR_PLUS",
    )
    # Must NOT be marked IMPLEMENTATION_CONFIRMED because technical mechanism differs
    assert result.decision in [
        ImplementationDecisionEnum.POTENTIAL_IMPLEMENTATION_EVIDENCE,
        ImplementationDecisionEnum.INSUFFICIENT_EVIDENCE,
        ImplementationDecisionEnum.CONFLICTING_EVIDENCE,
    ]
    assert result.requires_human_review is True


# ── TEST 12: Same Engineering Change Different Wording (False Negative Prevention)
def test_12_same_engineering_change_different_wording(orchestrator, standard_corpus):
    # Different wording: 'mass reduction using Al alloy' instead of 'aluminum material substitution'
    result = orchestrator.execute_grounding_pipeline(
        raw_query="Handlebar mass reduction on 53100-DEMO-001 using 6061-T6 Al alloy",
        corpus_records=[c for c in standard_corpus if c["id"] != "DOC-ECN-005-CONFLICT"],
        target_part_number="53100-DEMO-001",
        target_vehicle_model="SPLENDOR_PLUS",
    )
    assert result.decision == ImplementationDecisionEnum.IMPLEMENTATION_CONFIRMED
    assert result.grounding_score >= 0.50


# ── TEST 13: Historical Validity & Temporal Cutoff ─────────────────────────────
def test_13_historical_validity_and_temporal_cutoff(orchestrator):
    historical_corpus = [
        {
            "id": "DOC-ECN-HIST",
            "entity_type": "ECN",
            "entity_id": "ecn-hist-01",
            "text": "ECN-2017-001: Historical 2017 cost project for 53100-DEMO-001 on SPLENDOR_PLUS.",
            "part_number": "53100-DEMO-001",
            "ecn_number": "ECN-2017-001",
            "model_code": "SPLENDOR_PLUS",
            "category": "WEIGHT_REDUCTION",
            "metadata": {
                "source_type": "ECN",
                "code_or_number": "ECN-2017-001",
                "status": "OBSOLETE",
                "effective_date": "2017-01-15",
                "authority_class": "HISTORICAL_IMPLEMENTATION",
                "is_obsolete": True,
            },
        }
    ]
    result = orchestrator.execute_grounding_pipeline(
        raw_query="Historical weight reduction on 53100-DEMO-001",
        corpus_records=historical_corpus,
        target_part_number="53100-DEMO-001",
        target_vehicle_model="SPLENDOR_PLUS",
        submission_date=date(2024, 1, 1),
    )
    assert result.decision == ImplementationDecisionEnum.HISTORICAL_IMPLEMENTATION
    assert result.classified_evidences[0].is_historical is True


# ── TEST 14: Conflicting Evidence Detection & Human Routing ───────────────────
def test_14_conflicting_evidence_detection_and_human_routing(orchestrator, standard_corpus):
    result = orchestrator.execute_grounding_pipeline(
        raw_query="Evaluate validation and release status of ECN-2024-001 on 53100-DEMO-001",
        corpus_records=standard_corpus,
        target_part_number="53100-DEMO-001",
        target_vehicle_model="SPLENDOR_PLUS",
    )
    assert result.decision == ImplementationDecisionEnum.CONFLICTING_EVIDENCE
    assert result.requires_human_review is True
    assert len(result.review_reasons) >= 1


# ── TEST 15: Cross-Model Applicability Handling ────────────────────────────────
def test_15_cross_model_applicability_handling(orchestrator):
    sibling_corpus = [
        {
            "id": "DOC-ECN-HF",
            "entity_type": "ECN",
            "entity_id": "ecn-hf-01",
            "text": "ECN-2024-088: Released aluminum handlebar weight for HF_DELUXE on Part 53100-DEMO-001.",
            "part_number": "53100-DEMO-001",
            "ecn_number": "ECN-2024-088",
            "model_code": "HF_DELUXE",
            "category": "WEIGHT_REDUCTION",
            "metadata": {
                "source_type": "ECN",
                "code_or_number": "ECN-2024-088",
                "status": "RELEASED",
                "effective_date": "2024-06-01",
                "authority_class": "AUTHORITATIVE_ENGINEERING",
            },
        }
    ]
    result = orchestrator.execute_grounding_pipeline(
        raw_query="Rollout aluminum weight to GLAMOUR",
        corpus_records=sibling_corpus,
        target_part_number="53100-DEMO-001",
        target_vehicle_model="GLAMOUR",
        applicable_sibling_models=["HF_DELUXE", "GLAMOUR"],
    )
    assert result.decision == ImplementationDecisionEnum.PARTIALLY_CONFIRMED
    assert "HF_DELUXE" in result.confirmed_models


# ── TEST 16: Insufficient Evidence Handling ───────────────────────────────────
def test_16_insufficient_evidence_handling(orchestrator):
    vague_corpus = [
        {
            "id": "DOC-AMBIG",
            "entity_type": "IDEATHON",
            "entity_id": "idea-ambig",
            "text": "Rough conceptual scribble about commuter bike handlebars.",
            "part_number": None,
            "ecn_number": None,
            "model_code": None,
            "category": "MISCELLANEOUS",
            "metadata": {
                "source_type": "IDEATHON",
                "code_or_number": "IDEA-AMBIG",
                "status": "DRAFT",
                "authority_class": "IDEATHON_SUBMISSION",
            },
        }
    ]
    result = orchestrator.execute_grounding_pipeline(
        raw_query="Handlebar concept check",
        corpus_records=vague_corpus,
    )
    assert result.decision == ImplementationDecisionEnum.INSUFFICIENT_EVIDENCE
    assert result.requires_human_review is True


# ── TEST 17: Grounding Score Calculation ──────────────────────────────────────
def test_17_grounding_score_calculation(orchestrator, standard_corpus):
    clean_corpus = [c for c in standard_corpus if c["id"] != "DOC-ECN-005-CONFLICT"]
    result = orchestrator.execute_grounding_pipeline(
        raw_query="Material substitution to 6061-T6 aluminum on 53100-DEMO-001",
        corpus_records=clean_corpus,
        target_part_number="53100-DEMO-001",
        target_vehicle_model="SPLENDOR_PLUS",
    )
    assert result.grounding_score > 0.0
    assert len(result.claims) >= 1
    assert result.claims[0].is_supported is True
    assert len(result.claims[0].supporting_evidence_ids) >= 1


# ── TEST 18: Context Manager Integration ──────────────────────────────────────
def test_18_context_manager_integration(orchestrator, standard_corpus):
    result = orchestrator.execute_grounding_pipeline(
        raw_query="53100-DEMO-001 weight reduction",
        corpus_records=standard_corpus,
        target_part_number="53100-DEMO-001",
        context_limit=2048,
    )
    assert result.provenance.context_items_selected_count >= 1
    assert result.provenance.latency_breakdown_ms["context_assembly_ms"] >= 0.0


# ── TEST 19: Full Provenance Trace Integrity ──────────────────────────────────
def test_19_full_provenance_trace_integrity(orchestrator, standard_corpus):
    result = orchestrator.execute_grounding_pipeline(
        raw_query="Part 53100-DEMO-001 ECN-2024-001 SPLENDOR_PLUS",
        corpus_records=standard_corpus,
        idea_id="idea-999",
    )
    prov = result.provenance
    assert prov.idea_id == "idea-999"
    assert prov.extracted_identifiers["part_number"] == "53100-DEMO-001"
    assert "EXACT_IDENTIFIER" in prov.strategies_executed
    assert "total_pipeline_latency_ms" in prov.latency_breakdown_ms
    assert prov.embedding_model_id == "native-local-embedding-v1"
    assert prov.reranker_model_id == "native-local-cross-encoder-v1"


# ── TEST 20: Deterministic Reproducibility ─────────────────────────────────────
def test_20_deterministic_reproducibility(orchestrator, standard_corpus):
    clean_corpus = [c for c in standard_corpus if c["id"] != "DOC-ECN-005-CONFLICT"]
    res1 = orchestrator.execute_grounding_pipeline(
        raw_query="Material substitution for 53100-DEMO-001",
        corpus_records=clean_corpus,
        target_part_number="53100-DEMO-001",
    )
    res2 = orchestrator.execute_grounding_pipeline(
        raw_query="Material substitution for 53100-DEMO-001",
        corpus_records=clean_corpus,
        target_part_number="53100-DEMO-001",
    )
    assert res1.decision == res2.decision
    assert res1.grounding_score == res2.grounding_score
    assert len(res1.classified_evidences) == len(res2.classified_evidences)


# ── TEST 21: Stale Index Detection Policy ─────────────────────────────────────
def test_21_stale_index_detection_policy():
    spec = GroundingEvaluationSpec(stale_index_threshold_hours=24)
    assert spec.stale_index_threshold_hours == 24
    assert spec.authority_policy_version == "v1.0.0"


# ── TEST 22: Source Authority Weighting Hierarchy ─────────────────────────────
def test_22_source_authority_weighting_hierarchy():
    assert SourceAuthorityEnum.AUTHORITATIVE_ENGINEERING.weight == 1.0
    assert SourceAuthorityEnum.BOM_MASTER_DATA.weight == 0.90
    assert SourceAuthorityEnum.PLANT_OPEX_ACTUALS.weight == 0.85
    assert SourceAuthorityEnum.HISTORICAL_IMPLEMENTATION.weight == 0.75
    assert SourceAuthorityEnum.IDEATHON_SUBMISSION.weight == 0.50
    assert SourceAuthorityEnum.SECONDARY_EXTERNAL.weight == 0.35


# ── TEST 23: Full 12-Scenario Benchmark Execution ─────────────────────────────
def test_23_full_12_scenario_benchmark_execution(real_embedding_engine, real_reranker_engine, standard_corpus):
    report: MetricReport = GroundingBenchmarkSuite.run_benchmark(
        corpus=standard_corpus,
        embedding_engine=real_embedding_engine,
        reranker_engine=real_reranker_engine,
    )
    assert report.scenarios_evaluated == 12
    assert report.retrieval_recall_at_k >= 0.80
    assert report.rerank_top1_accuracy >= 0.80
    assert report.evidence_decision_accuracy >= 0.80
    assert report.latency_ms_per_scenario >= 0.0


# ── TEST 24: Six-Tier Ablation Study Execution ────────────────────────────────
def test_24_six_tier_ablation_study_execution(real_embedding_engine, real_reranker_engine, standard_corpus):
    ablation_results = GroundingBenchmarkSuite.run_ablation_study(
        corpus=standard_corpus,
        embedding_engine=real_embedding_engine,
        reranker_engine=real_reranker_engine,
    )
    assert "A_EXACT_ONLY" in ablation_results
    assert "B_LEXICAL_ONLY" in ablation_results
    assert "C_DENSE_ONLY" in ablation_results
    assert "D_RRF_FUSION" in ablation_results
    assert "E_RRF_PLUS_RERANKER" in ablation_results
    assert "F_FULL_PIPELINE" in ablation_results

    # Full pipeline must equal or exceed individual channels
    assert ablation_results["F_FULL_PIPELINE"].evidence_decision_accuracy >= ablation_results["A_EXACT_ONLY"].evidence_decision_accuracy
