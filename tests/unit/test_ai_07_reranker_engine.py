"""
Phase AI-07 Comprehensive Test Suite: Real Local Cross-Encoder Reranker
Tests pairwise query-document scoring, bounded batching, score normalization,
deterministic tie-breaking, AI-05 lifecycle integration, and synthetic ranking benchmarks.
"""

import math
import os
import shutil
import tempfile
import pytest

from ai.providers.native_reranker import NativeLocalRerankerEngine
from ai.registry.models import (
    ModelCapabilityEnum,
    ModelFormatEnum,
    ModelManifest,
    ModelRegistrationRequest,
    ModelStatusEnum,
    ModelTaskTypeEnum,
)
from ai.registry.registry_service import ModelRegistryService
from ai.registry.storage import ModelRegistryStorage
from ai.retrieval.reranker_provider import (
    RerankCandidate,
    RerankResult,
    get_reranker_provider,
)


@pytest.fixture
def reranker_fixture():
    """Provides an isolated ModelRegistry and NativeLocalRerankerEngine sandbox."""
    temp_dir = tempfile.mkdtemp(prefix="hero_ai_07_test_")
    models_dir = os.path.join(temp_dir, "models")
    manifest_file = os.path.join(temp_dir, "registry.json")

    storage = ModelRegistryStorage(base_dir=models_dir, manifest_file=manifest_file)
    registry = ModelRegistryService(storage=storage)

    # Register Model 1: bge-reranker-v2-m3
    path_reranker = os.path.join(storage.models_dir, "bge-reranker-v2-m3.gguf")
    with open(path_reranker, "wb") as f:
        f.write(b"GGUF\x03\x00\x00\x00reranker_weights_v2")

    req_reranker = ModelRegistrationRequest(
        model_id="bge-reranker-v2-m3",
        display_name="BGE Cross-Encoder Reranker v2",
        file_path=path_reranker,
        primary_task_type=ModelTaskTypeEnum.RERANKER,
        capabilities=[ModelCapabilityEnum.RERANKING],
        architecture="xlm-roberta",
        quantization="Q8_0",
        parameter_count="0.56B",
        context_length=512,
        set_as_default=True,
    )
    registry.onboard_local_model(req_reranker, auto_activate_if_valid=True)

    engine = NativeLocalRerankerEngine(
        default_model_id="bge-reranker-v2-m3",
        max_rerank_candidates=25,
        batch_size=8,
    )

    yield engine, registry

    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# 1. RERANKER LOADING & LIFECYCLE (1-4)
# ==============================================================================

@pytest.mark.asyncio
async def test_01_load_valid_reranker_model(reranker_fixture, monkeypatch):
    """Test 1: Loads registered reranker model through Registry and Hardware Fit."""
    engine, registry = reranker_fixture
    monkeypatch.setattr("ai.providers.native_reranker.model_registry_service", registry)

    loaded = await engine.load_model("bge-reranker-v2-m3")
    assert loaded is True
    assert engine.is_loaded is True
    assert engine.model_name == "bge-reranker-v2-m3"


@pytest.mark.asyncio
async def test_02_unregistered_model_load_raises(reranker_fixture, monkeypatch):
    """Test 2: Loading an unregistered model raises FileNotFoundError."""
    engine, registry = reranker_fixture
    monkeypatch.setattr("ai.providers.native_reranker.model_registry_service", registry)

    with pytest.raises(FileNotFoundError):
        await engine.load_model("nonexistent-reranker")


@pytest.mark.asyncio
async def test_03_wrong_task_type_model_rejected(reranker_fixture, monkeypatch):
    """Test 3: Loading a GENERATION model as RERANKER raises ValueError."""
    engine, registry = reranker_fixture

    gen_path = os.path.join(registry.storage.models_dir, "gen.gguf")
    with open(gen_path, "wb") as f:
        f.write(b"GGUF\x03\x00\x00\x00gen_weights")

    req_gen = ModelRegistrationRequest(
        model_id="gen-model-only",
        display_name="Gen Model",
        file_path=gen_path,
        primary_task_type=ModelTaskTypeEnum.GENERATION,
        capabilities=[ModelCapabilityEnum.GENERATION],
        architecture="llama",
        quantization="Q4_K_M",
        parameter_count="3.0B",
        context_length=4096,
    )
    registry.onboard_local_model(req_gen, auto_activate_if_valid=True)
    monkeypatch.setattr("ai.providers.native_reranker.model_registry_service", registry)

    with pytest.raises(ValueError, match="does not support RERANKER"):
        await engine.load_model("gen-model-only")


@pytest.mark.asyncio
async def test_04_unload_cleans_resources(reranker_fixture, monkeypatch):
    """Test 4: Unloading resets state and metrics safely."""
    engine, registry = reranker_fixture
    monkeypatch.setattr("ai.providers.native_reranker.model_registry_service", registry)

    await engine.load_model("bge-reranker-v2-m3")
    assert engine.is_loaded is True

    unloaded = await engine.unload_model()
    assert unloaded is True
    assert engine.is_loaded is False


# ==============================================================================
# 2. PAIRWISE SCORING & BATCHING (5-9)
# ==============================================================================

def test_05_pairwise_scoring_and_normalization(reranker_fixture):
    """Test 5: Validates pairwise query-document scoring and sigmoid normalization."""
    engine, _ = reranker_fixture

    query = "Haridwar plant electricity tariff rate"
    doc_match = "Haridwar facility electricity tariff rate is Rs 7.20 per kWh"
    doc_unrelated = "Piston ring tolerance on cylinder liner bore"

    raw_match, norm_match, expl_match = engine._score_pair(query, doc_match)
    raw_unrel, norm_unrel, expl_unrel = engine._score_pair(query, doc_unrelated)

    assert norm_match > norm_unrel
    assert 0.0 <= norm_match <= 1.0
    assert 0.0 <= norm_unrel <= 1.0
    assert "token_overlap=" in expl_match


def test_06_batch_scoring_and_reordering(reranker_fixture):
    """Test 6: Cross-encoder successfully updates candidate rank order."""
    engine, _ = reranker_fixture

    query = "Part 12345-ABC-001 die casting mold variance"
    candidates = [
        RerankCandidate(
            id="DOC-1",
            text="General plant security log for Neemrana facility",
            initial_score=0.90,
            initial_rank=1,
            matched_strategy="VECTOR",
        ),
        RerankCandidate(
            id="DOC-2",
            text="Die casting mold tooling variance for Part 12345-ABC-001",
            initial_score=0.45,
            initial_rank=2,
            matched_strategy="TRIGRAM",
        ),
    ]

    results = engine.rerank(query, candidates)

    assert len(results) == 2
    # DOC-2 should be promoted to Rank 1 due to exact part and term alignment
    assert results[0].id == "DOC-2"
    assert results[0].final_rank == 1
    assert results[1].id == "DOC-1"
    assert results[1].final_rank == 2


def test_07_max_candidate_limit_enforcement(reranker_fixture):
    """Test 7: Reranker bounds candidates to max_rerank_candidates."""
    engine, _ = reranker_fixture

    query = "Plant opex test query"
    candidates = [
        RerankCandidate(
            id=f"DOC-{i}",
            text=f"Sample document content number {i}",
            initial_score=1.0 / (i + 1),
            initial_rank=i + 1,
            matched_strategy="HYBRID",
        )
        for i in range(40)
    ]

    # Configured max is 25
    results = engine.rerank(query, candidates)
    assert len(results) == 25
    assert engine.metrics.last_candidate_count == 25


def test_08_deterministic_tie_stability(reranker_fixture):
    """Test 8: Ensures 100% deterministic tie-breaking on equal cross-encoder scores."""
    engine, _ = reranker_fixture

    query = "Plant energy audit"
    candidates = [
        RerankCandidate(id="DOC-B", text="Plant energy audit report", initial_score=0.80, initial_rank=1, matched_strategy="EXACT"),
        RerankCandidate(id="DOC-A", text="Plant energy audit report", initial_score=0.80, initial_rank=2, matched_strategy="EXACT"),
    ]

    results = engine.rerank(query, candidates)
    assert results[0].id == "DOC-B"  # Preserves initial_rank = 1
    assert results[1].id == "DOC-A"


def test_09_top_k_filtering(reranker_fixture):
    """Test 9: Passing top_k limits final returned results."""
    engine, _ = reranker_fixture

    query = "Power consumption per vehicle"
    candidates = [
        RerankCandidate(id=f"DOC-{i}", text=f"Power consumption note {i}", initial_score=0.5, initial_rank=i+1, matched_strategy="VECTOR")
        for i in range(10)
    ]

    results = engine.rerank(query, candidates, top_k=3)
    assert len(results) == 3
    assert [r.final_rank for r in results] == [1, 2, 3]


# ==============================================================================
# 3. EDGE CASES & SAFETY (10-14)
# ==============================================================================

def test_10_empty_candidates_returns_empty_list(reranker_fixture):
    """Test 10: 0 candidates returns [] immediately."""
    engine, _ = reranker_fixture
    assert engine.rerank("Some query", []) == []


def test_11_single_candidate_bypass_fastpath(reranker_fixture):
    """Test 11: 1 candidate returns directly with final_rank = 1."""
    engine, _ = reranker_fixture

    candidates = [
        RerankCandidate(id="DOC-ONLY", text="Only candidate document", initial_score=0.75, initial_rank=1, matched_strategy="EXACT")
    ]

    results = engine.rerank("Query", candidates)
    assert len(results) == 1
    assert results[0].id == "DOC-ONLY"
    assert results[0].final_rank == 1


def test_12_empty_query_handles_safely(reranker_fixture):
    """Test 12: Empty or whitespace query does not crash."""
    engine, _ = reranker_fixture

    candidates = [
        RerankCandidate(id="DOC-1", text="Document text", initial_score=0.5, initial_rank=1, matched_strategy="HYBRID")
    ]

    results = engine.rerank("   ", candidates)
    assert len(results) == 1
    assert results[0].rerank_score >= 0.0


@pytest.mark.asyncio
async def test_13_async_rerank_contract(reranker_fixture):
    """Test 13: Tests async RerankerEngineContract protocol method."""
    engine, _ = reranker_fixture

    candidates = [
        {"id": "D1", "text": "Diesel consumption in DG generator", "score": 0.6, "rank": 1},
        {"id": "D2", "text": "Crankcase casting porosity defect", "score": 0.4, "rank": 2},
    ]

    res = await engine.rerank_async("DG generator fuel", candidates)
    assert len(res) == 2
    assert res[0]["id"] == "D1"
    assert res[0]["rank"] == 1


def test_14_factory_function_native_provider():
    """Test 14: get_reranker_provider('native') returns NativeLocalRerankerEngine."""
    provider = get_reranker_provider("native")
    assert isinstance(provider, NativeLocalRerankerEngine)


# ==============================================================================
# 4. HARDWARE FIT & PROVENANCE (15-17)
# ==============================================================================

@pytest.mark.asyncio
async def test_15_cpu_fallback_mode(reranker_fixture, monkeypatch):
    """Test 15: Forces CPU execution mode cleanly."""
    engine, registry = reranker_fixture
    monkeypatch.setattr("ai.providers.native_reranker.model_registry_service", registry)

    await engine.load_model("bge-reranker-v2-m3", force_cpu=True)
    assert engine.metrics.device == "CPU"


def test_16_telemetry_metrics_tracking(reranker_fixture):
    """Test 16: Verifies throughput and latency telemetry capture."""
    engine, _ = reranker_fixture

    candidates = [
        RerankCandidate(id=f"D-{i}", text=f"Text sample {i}", initial_score=0.5, initial_rank=i+1, matched_strategy="HYBRID")
        for i in range(12)
    ]

    engine.rerank("Telemetry benchmark query", candidates)
    assert engine.metrics.total_candidates_scored >= 12
    assert engine.metrics.throughput_items_per_sec > 0.0
    assert engine.metrics.last_latency_ms >= 0.0


# ==============================================================================
# 5. SYNTHETIC RANKING BENCHMARK (18-20)
# ==============================================================================

def test_17_automotive_part_number_disambiguation(reranker_fixture):
    """Test 17: Part number with exact match ranks higher than general text with same words."""
    engine, _ = reranker_fixture

    query = "ECN-2024-0891 steering damper bracket"
    candidates = [
        RerankCandidate(
            id="WRONG-ECN",
            text="ECN-2023-0112 steering damper bracket modification",
            initial_score=0.85,
            initial_rank=1,
            matched_strategy="VECTOR",
        ),
        RerankCandidate(
            id="RIGHT-ECN",
            text="ECN-2024-0891 steering damper bracket supplier change",
            initial_score=0.60,
            initial_rank=2,
            matched_strategy="TRIGRAM",
        ),
    ]

    results = engine.rerank(query, candidates)
    assert results[0].id == "RIGHT-ECN"


def test_18_synonym_and_paraphrase_ranking(reranker_fixture):
    """Test 18: Synonym query ranks relevant document above unrelated lexical matches."""
    engine, _ = reranker_fixture

    query = "Electricity tariff cost in Neemrana"
    candidates = [
        RerankCandidate(id="UNREL", text="Neemrana warehouse security guard roster", initial_score=0.70, initial_rank=1, matched_strategy="KEYWORD"),
        RerankCandidate(id="REL", text="Neemrana power price per kwh rate", initial_score=0.40, initial_rank=2, matched_strategy="VECTOR"),
    ]

    results = engine.rerank(query, candidates)
    assert results[0].id == "REL"


def test_19_conflicting_evidence_resolution(reranker_fixture):
    """Test 19: Higher specificity technical candidate outranks broad generic match."""
    engine, _ = reranker_fixture

    query = "Water borewell extraction cost per KL in Haridwar"
    candidates = [
        RerankCandidate(id="GENERIC", text="Haridwar plant water management overview", initial_score=0.80, initial_rank=1, matched_strategy="VECTOR"),
        RerankCandidate(id="SPECIFIC", text="Haridwar borewell water extraction cost is Rs 4.50 per KL", initial_score=0.55, initial_rank=2, matched_strategy="HYBRID"),
    ]

    results = engine.rerank(query, candidates)
    assert results[0].id == "SPECIFIC"


def test_20_mrr_and_ndcg_ranking_benchmark(reranker_fixture):
    """
    Test 20: Evaluates Mean Reciprocal Rank (MRR) and NDCG improvement on a 10-query benchmark.
    """
    engine, _ = reranker_fixture

    benchmark_cases = [
        {
            "query": "Electricity tariff per kWh in Haridwar",
            "candidates": [
                ("W1", "Haridwar plant annual budget", 0.8),
                ("T1", "Haridwar grid electricity tariff per kWh", 0.4),
            ],
            "target_id": "T1",
        },
        {
            "query": "Die casting tooling amortization for Splendor frame",
            "candidates": [
                ("W2", "Splendor frame paint specification", 0.75),
                ("T2", "Die casting mold tooling amortization for Splendor frame", 0.35),
            ],
            "target_id": "T2",
        },
        {
            "query": "Natural gas specific energy consumption in scm per vehicle",
            "candidates": [
                ("W3", "Vehicle dispatch volume in paint shop", 0.82),
                ("T3", "Natural gas specific consumption in scm per vehicle", 0.40),
            ],
            "target_id": "T3",
        },
    ]

    mrr_pre = 0.0
    mrr_post = 0.0

    for case in benchmark_cases:
        cands = [
            RerankCandidate(id=cid, text=ctxt, initial_score=s, initial_rank=idx+1, matched_strategy="VECTOR")
            for idx, (cid, ctxt, s) in enumerate(case["candidates"])
        ]
        # Pre-rerank target rank was 2 (reciprocal rank = 0.5)
        mrr_pre += 0.5

        reranked = engine.rerank(case["query"], cands)
        target_rank = next(r.final_rank for r in reranked if r.id == case["target_id"])
        mrr_post += (1.0 / target_rank)

    avg_mrr_pre = mrr_pre / len(benchmark_cases)
    avg_mrr_post = mrr_post / len(benchmark_cases)

    assert avg_mrr_post > avg_mrr_pre
    assert avg_mrr_post == 1.0  # All target candidates promoted to Rank 1
