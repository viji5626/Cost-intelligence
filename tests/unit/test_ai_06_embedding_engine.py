"""
Phase AI-06 Comprehensive Test Suite: Real Local Dense Embedding Engine & Native Vector Store
Tests real local embeddings, dynamic dimensionality (D=384, D=768, D=1024), L2 normalization,
HNSW index parameters, embedding space versioning, re-indexing detection, and semantic retrieval.
"""

import math
import os
import shutil
import tempfile
import pytest

from ai.providers.native_embedding import NativeLocalEmbeddingEngine
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
from ai.retrieval.vector_store import (
    EmbeddingSpaceRecord,
    EmbeddingSpaceStatusEnum,
    EmbeddingSpaceVersionManager,
    HNSWIndexConfig,
    NativeVectorStore,
    VectorStoreRecord,
)


@pytest.fixture
def embedding_fixture():
    """Provides an isolated ModelRegistry, VectorStore, and NativeLocalEmbeddingEngine sandbox."""
    temp_dir = tempfile.mkdtemp(prefix="hero_ai_06_test_")
    models_dir = os.path.join(temp_dir, "models")
    manifest_file = os.path.join(temp_dir, "registry.json")

    storage = ModelRegistryStorage(base_dir=models_dir, manifest_file=manifest_file)
    registry = ModelRegistryService(storage=storage)

    # Register Model 1: bge-small (384d)
    path_384 = os.path.join(storage.models_dir, "bge-small-en.gguf")
    with open(path_384, "wb") as f:
        f.write(b"GGUF\x03\x00\x00\x00weights_384d")

    req_384 = ModelRegistrationRequest(
        model_id="bge-small-en-v1.5",
        display_name="BGE Small English 384d",
        file_path=path_384,
        primary_task_type=ModelTaskTypeEnum.EMBEDDING,
        capabilities=[ModelCapabilityEnum.EMBEDDING],
        architecture="bert",
        quantization="Q8_0",
        parameter_count="0.33B",
        embedding_dimension=384,
        context_length=512,
        set_as_default=True,
    )
    registry.onboard_local_model(req_384, auto_activate_if_valid=True)

    # Register Model 2: bge-base (768d)
    path_768 = os.path.join(storage.models_dir, "bge-base-en.gguf")
    with open(path_768, "wb") as f:
        f.write(b"GGUF\x03\x00\x00\x00weights_768d")

    req_768 = ModelRegistrationRequest(
        model_id="bge-base-en-v1.5",
        display_name="BGE Base English 768d",
        file_path=path_768,
        primary_task_type=ModelTaskTypeEnum.EMBEDDING,
        capabilities=[ModelCapabilityEnum.EMBEDDING],
        architecture="bert",
        quantization="Q8_0",
        parameter_count="0.7B",
        embedding_dimension=768,
        context_length=512,
    )
    registry.onboard_local_model(req_768, auto_activate_if_valid=True)

    # Register Model 3: bge-large (1024d)
    path_1024 = os.path.join(storage.models_dir, "bge-large-en.gguf")
    with open(path_1024, "wb") as f:
        f.write(b"GGUF\x03\x00\x00\x00weights_1024d")

    req_1024 = ModelRegistrationRequest(
        model_id="bge-large-en-v1.5",
        display_name="BGE Large English 1024d",
        file_path=path_1024,
        primary_task_type=ModelTaskTypeEnum.EMBEDDING,
        capabilities=[ModelCapabilityEnum.EMBEDDING],
        architecture="bert",
        quantization="Q8_0",
        parameter_count="1.3B",
        embedding_dimension=1024,
        context_length=512,
    )
    registry.onboard_local_model(req_1024, auto_activate_if_valid=True)

    engine = NativeLocalEmbeddingEngine(default_model_id="bge-small-en-v1.5", fallback_dimension=384)
    vector_store = NativeVectorStore(
        embedding_space=EmbeddingSpaceRecord(
            space_id="hero-bge-small-d384-v1",
            model_id="bge-small-en-v1.5",
            model_hash=registry.get_model("bge-small-en-v1.5").sha256_checksum,
            dimension=384,
        )
    )

    yield engine, registry, vector_store

    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# 1. EMBEDDING GENERATION, DIMENSION & NORMALIZATION (1-5)
# ==============================================================================

@pytest.mark.asyncio
async def test_01_load_and_embed_single_text(embedding_fixture, monkeypatch):
    """Test 1: Loads registered embedding model and verifies 384-d output."""
    engine, registry, _ = embedding_fixture
    monkeypatch.setattr("ai.providers.native_embedding.model_registry_service", registry)

    loaded = await engine.load_model("bge-small-en-v1.5")
    assert loaded is True
    assert engine.dimension == 384

    vec = engine.embed_text("Plant OPEX benchmarking for vehicle manufacturing")
    assert len(vec) == 384
    norm = math.sqrt(sum(x * x for x in vec))
    assert pytest.approx(norm, rel=1e-5) == 1.0


@pytest.mark.asyncio
async def test_02_dynamic_dimension_switching_768d_and_1024d(embedding_fixture, monkeypatch):
    """Test 2: Switches to 768-d and 1024-d models dynamically."""
    engine, registry, _ = embedding_fixture
    monkeypatch.setattr("ai.providers.native_embedding.model_registry_service", registry)

    # 1. 768-d
    await engine.load_model("bge-base-en-v1.5")
    assert engine.dimension == 768
    vec_768 = engine.embed_text("Electricity tariff rate in Haridwar")
    assert len(vec_768) == 768

    # 2. 1024-d
    await engine.load_model("bge-large-en-v1.5")
    assert engine.dimension == 1024
    vec_1024 = engine.embed_text("BOM cost breakdown for chassis assembly")
    assert len(vec_1024) == 1024


def test_03_strict_l2_unit_normalization(embedding_fixture):
    """Test 3: Validates that all generated vectors have exact L2 norm = 1.0."""
    engine, _, _ = embedding_fixture

    sample_texts = [
        "Hero Splendor engine casting raw material variance",
        "Short text",
        "Very long complex technical text describing paint shop natural gas specific energy consumption in scm per vehicle",
    ]

    for text in sample_texts:
        vec = engine.embed_text(text)
        norm = math.sqrt(sum(v * v for v in vec))
        assert pytest.approx(norm, rel=1e-5) == 1.0


def test_04_batch_embedding_with_progress_and_chunking(embedding_fixture):
    """Test 4: Batch embedding processes chunks and reports progress."""
    engine, _, _ = embedding_fixture

    texts = [f"Engineering change note record {i} for supplier tooling" for i in range(25)]
    progress_snapshots = []

    def on_progress(done, total):
        progress_snapshots.append((done, total))

    results = engine.embed_batch(texts, batch_size=8, progress_callback=on_progress)

    assert len(results) == 25
    assert len(results[0]) == 384
    assert len(progress_snapshots) >= 3
    assert progress_snapshots[-1] == (25, 25)
    assert engine.metrics.throughput_items_per_sec > 0.0


@pytest.mark.asyncio
async def test_05_async_contract_embed_texts(embedding_fixture):
    """Test 5: Tests async EmbeddingEngineContract embed_texts() method."""
    engine, _, _ = embedding_fixture

    texts = ["Chassis frame weld variance", "Paint shop primer viscosity"]
    res = await engine.embed_texts(texts)

    assert len(res) == 2
    assert len(res[0]) == 384
    assert engine.is_normalized() is True
    assert engine.get_dimension() == 384


# ==============================================================================
# 2. VECTOR STORAGE & HNSW INDEXING (6-10)
# ==============================================================================

def test_06_hnsw_ddl_generation():
    """Test 6: Generates valid PostgreSQL pgvector table and HNSW index DDL."""
    store = NativeVectorStore(
        embedding_space=EmbeddingSpaceRecord(
            space_id="test-space-d384",
            model_id="bge-small-en-v1.5",
            model_hash="abc123hash",
            dimension=384,
        ),
        hnsw_config=HNSWIndexConfig(m=16, ef_construction=64, ef_search=64, metric="cosine")
    )

    ddl = store.get_pgvector_table_ddl("plant_opex_vectors")

    assert "CREATE TABLE IF NOT EXISTS plant_opex_vectors" in ddl
    assert "embedding vector(384) NOT NULL" in ddl
    assert "USING hnsw (embedding vector_cosine_ops)" in ddl
    assert "WITH (m = 16, ef_construction = 64)" in ddl


def test_07_insert_and_similarity_search(embedding_fixture):
    """Test 7: Inserts vectors into store and performs cosine similarity search."""
    engine, _, vector_store = embedding_fixture

    # Insert test items
    texts = [
        ("ID-001", "PLANT_OPEX", "Electricity grid tariff rate per kWh in Neemrana plant"),
        ("ID-002", "PLANT_OPEX", "Water borewell extraction cost in Haridwar facility"),
        ("ID-003", "PART_BOM", "Die casting mold tooling amortisation for Splendor frame"),
    ]

    for entity_id, entity_type, txt in texts:
        vec = engine.embed_text(txt)
        rec = VectorStoreRecord(
            entity_type=entity_type,
            entity_id=entity_id,
            content_text=txt,
            embedding=vec,
            embedding_space_id=vector_store.space_manager.active_space.space_id,
            embedding_model_id=vector_store.space_manager.active_space.model_id,
            embedding_dimension=384,
        )
        vector_store.insert_record(rec)

    assert vector_store.count_records() == 3

    # Query: electricity costs
    q_vec = engine.embed_text("power tariff and kwh cost")
    matches = vector_store.similarity_search(q_vec, top_k=2)

    assert len(matches) > 0
    top_doc, score = matches[0]
    assert top_doc.entity_id == "ID-001"
    assert score > 0.1


def test_08_incompatible_dimension_rejection(embedding_fixture):
    """Test 8: Attempting to insert a 768-d vector into a 384-d space raises ValueError."""
    _, _, vector_store = embedding_fixture

    bad_record = VectorStoreRecord(
        entity_type="PART_BOM",
        entity_id="PART-999",
        content_text="Sample",
        embedding=[0.1] * 768,  # Incompatible 768-d
        embedding_space_id=vector_store.space_manager.active_space.space_id,
        embedding_model_id="bge-base-en-v1.5",
        embedding_dimension=768,
    )

    with pytest.raises(ValueError, match="Vector dimension mismatch"):
        vector_store.insert_record(bad_record)


def test_09_query_vector_dimension_mismatch_rejection(embedding_fixture):
    """Test 9: Passing wrong dimension query vector raises ValueError."""
    _, _, vector_store = embedding_fixture

    with pytest.raises(ValueError, match="Query vector dimension mismatch"):
        vector_store.similarity_search([0.1] * 512, top_k=5)


def test_10_batched_vector_insertion(embedding_fixture):
    """Test 10: Inserts multiple records in batch cleanly."""
    engine, _, vector_store = embedding_fixture

    records = [
        VectorStoreRecord(
            entity_type="PART_BOM",
            entity_id=f"PART-{i:03d}",
            content_text=f"Part specification {i}",
            embedding=engine.embed_text(f"Part specification {i}"),
            embedding_space_id=vector_store.space_manager.active_space.space_id,
            embedding_model_id=vector_store.space_manager.active_space.model_id,
            embedding_dimension=384,
        )
        for i in range(10)
    ]

    inserted_ids = vector_store.insert_batch(records)
    assert len(inserted_ids) == 10
    assert vector_store.count_records() >= 10


# ==============================================================================
# 3. EMBEDDING SPACE VERSIONING & RE-INDEXING DETECTION (11-14)
# ==============================================================================

def test_11_reindex_required_detection(embedding_fixture):
    """Test 11: Detects re-indexing requirement when model or dimension changes."""
    _, registry, vector_store = embedding_fixture
    current_space = vector_store.space_manager.active_space.space_id

    # 1. Target model with different dimension (768d vs current 384d)
    manifest_768 = registry.get_model("bge-base-en-v1.5")
    reindex_needed = vector_store.space_manager.detect_reindex_needed(current_space, manifest_768)
    assert reindex_needed is True

    # 2. Same model manifest -> No reindex needed
    manifest_384 = registry.get_model("bge-small-en-v1.5")
    reindex_same = vector_store.space_manager.detect_reindex_needed(current_space, manifest_384)
    assert reindex_same is False


def test_12_staged_space_migration_safety(embedding_fixture):
    """Test 12: Stages new embedding space without destroying old space before activation."""
    _, registry, vector_store = embedding_fixture
    mgr = vector_store.space_manager
    old_space_id = mgr.active_space.space_id

    # Stage new 768-d space
    staged = mgr.stage_new_space(
        new_space_id="hero-bge-base-d768-v2",
        model_id="bge-base-en-v1.5",
        model_hash=registry.get_model("bge-base-en-v1.5").sha256_checksum,
        dimension=768,
    )

    assert staged.status == EmbeddingSpaceStatusEnum.STAGED
    assert mgr.active_space.space_id == old_space_id  # Old space still active!

    # Promote staged space
    mgr.activate_staged_space("hero-bge-base-d768-v2")
    assert mgr.active_space.space_id == "hero-bge-base-d768-v2"
    assert mgr.active_space.dimension == 768


def test_13_activate_nonexistent_space_raises(embedding_fixture):
    """Test 13: Promoting a nonexistent space ID raises KeyError."""
    _, _, vector_store = embedding_fixture
    with pytest.raises(KeyError):
        vector_store.space_manager.activate_staged_space("nonexistent-space-id")


# ==============================================================================
# 4. FAILURE RESILIENCE, UNLOAD & VALIDATION (14-17)
# ==============================================================================

@pytest.mark.asyncio
async def test_14_unregistered_model_load_raises(embedding_fixture, monkeypatch):
    """Test 14: Attempting to load an unregistered embedding model raises FileNotFoundError."""
    engine, registry, _ = embedding_fixture
    monkeypatch.setattr("ai.providers.native_embedding.model_registry_service", registry)

    with pytest.raises(FileNotFoundError):
        await engine.load_model("ghost-model-384d")


@pytest.mark.asyncio
async def test_15_wrong_task_type_model_rejected(embedding_fixture, monkeypatch):
    """Test 15: Loading a GENERATION-only model as EMBEDDING raises ValueError."""
    engine, registry, _ = embedding_fixture

    # Register a GENERATION-only model
    gen_path = os.path.join(registry.storage.models_dir, "gen-only.gguf")
    with open(gen_path, "wb") as f:
        f.write(b"GGUF\x03\x00\x00\x00gen_weights")

    req_gen = ModelRegistrationRequest(
        model_id="gen-only-model",
        display_name="Gen Only Model",
        file_path=gen_path,
        primary_task_type=ModelTaskTypeEnum.GENERATION,
        capabilities=[ModelCapabilityEnum.GENERATION],
        architecture="llama",
        quantization="Q4_K_M",
        parameter_count="3.0B",
        context_length=4096,
    )
    registry.onboard_local_model(req_gen, auto_activate_if_valid=True)
    monkeypatch.setattr("ai.providers.native_embedding.model_registry_service", registry)

    with pytest.raises(ValueError, match="does not support EMBEDDING"):
        await engine.load_model("gen-only-model")


@pytest.mark.asyncio
async def test_16_unload_model_cleans_resources(embedding_fixture, monkeypatch):
    """Test 16: unload_model() cleanly resets engine state."""
    engine, registry, _ = embedding_fixture
    monkeypatch.setattr("ai.providers.native_embedding.model_registry_service", registry)

    await engine.load_model("bge-small-en-v1.5")
    assert engine.is_loaded is True

    unloaded = await engine.unload_model()
    assert unloaded is True
    assert engine.is_loaded is False


def test_17_empty_text_returns_zero_vector(embedding_fixture):
    """Test 17: Empty or whitespace-only text safely returns a zero-vector."""
    engine, _, _ = embedding_fixture

    v_empty = engine.embed_text("")
    v_ws = engine.embed_text("   \n\t  ")

    assert len(v_empty) == 384
    assert all(x == 0.0 for x in v_empty)
    assert len(v_ws) == 384
    assert all(x == 0.0 for x in v_ws)


# ==============================================================================
# 5. SEMANTIC RETRIEVAL BENCHMARK QUALITY CHECK (18-20)
# ==============================================================================

def test_18_semantic_similarity_relative_ordering(embedding_fixture):
    """Test 18: Evaluates relative cosine similarity scores across domain queries."""
    engine, _, _ = embedding_fixture

    anchor = "Plant OPEX electricity cost per vehicle in Haridwar"
    paraphrase = "Haridwar factory power expenditure per unit produced"
    unrelated = "Piston ring tolerance on cylinder liner bore"

    v_anchor = engine.embed_text(anchor)
    v_paraphrase = engine.embed_text(paraphrase)
    v_unrelated = engine.embed_text(unrelated)

    sim_paraphrase = sum(a * b for a, b in zip(v_anchor, v_paraphrase))
    sim_unrelated = sum(a * b for a, b in zip(v_anchor, v_unrelated))

    assert sim_paraphrase > sim_unrelated
    assert sim_paraphrase > 0.15


def test_19_synonym_similarity_ranking(embedding_fixture):
    """Test 19: Tests synonym detection (e.g., tariff vs price vs rate)."""
    engine, _, _ = embedding_fixture

    anchor = "grid tariff rate per kwh"
    synonym = "grid power price per kwh"
    different = "crankshaft heat treatment cycle"

    v_a = engine.embed_text(anchor)
    v_s = engine.embed_text(synonym)
    v_d = engine.embed_text(different)

    sim_syn = sum(x * y for x, y in zip(v_a, v_s))
    sim_diff = sum(x * y for x, y in zip(v_a, v_d))

    assert sim_syn > sim_diff


def test_20_entity_type_filtered_similarity_search(embedding_fixture):
    """Test 20: Filters similarity search results by entity_type."""
    engine, _, vector_store = embedding_fixture

    r1 = VectorStoreRecord(
        entity_type="PLANT_OPEX",
        entity_id="OPEX-1",
        content_text="DG generator diesel consumption",
        embedding=engine.embed_text("DG generator diesel consumption"),
        embedding_space_id=vector_store.space_manager.active_space.space_id,
        embedding_model_id="bge-small-en-v1.5",
        embedding_dimension=384,
    )
    r2 = VectorStoreRecord(
        entity_type="PART_BOM",
        entity_id="BOM-1",
        content_text="Diesel fuel injection pump assembly",
        embedding=engine.embed_text("Diesel fuel injection pump assembly"),
        embedding_space_id=vector_store.space_manager.active_space.space_id,
        embedding_model_id="bge-small-en-v1.5",
        embedding_dimension=384,
    )

    vector_store.insert_record(r1)
    vector_store.insert_record(r2)

    q = engine.embed_text("diesel consumption")
    matches = vector_store.similarity_search(q, top_k=5, filter_entity_type="PLANT_OPEX")

    assert len(matches) == 1
    assert matches[0][0].entity_id == "OPEX-1"
