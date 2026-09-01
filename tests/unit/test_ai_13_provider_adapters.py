"""
Unit Tests for Phase AI-13: Provider Adapter Layer
Covers all adapter contracts, native adapters, Ollama & LM Studio test doubles,
OpenAI-compatible adapter, local Vision/OCR contract, mock simulation isolation,
provider registry discovery, policy-driven task fallbacks, no-silent-fallback enforcement,
and AI-02/AI-03 safety gate preservation.
"""

import asyncio
import io
import json
import urllib.error
import pytest
from unittest.mock import MagicMock, patch

from ai.core.contracts import ModelFormatEnum, ModelProvenance, ModelStatusEnum, TaskType
from ai.providers.adapter_contracts import (
    BaseProviderAdapter,
    EmbeddingAdapter,
    FallbackExecutionRecord,
    FallbackPolicy,
    InferenceAdapter,
    ProviderHealthReport,
    ProviderHealthStatusEnum,
    ProviderTelemetry,
    ProviderTypeEnum,
    RerankerAdapter,
    VisionOCRAdapter,
)
from ai.providers.adapters.lm_studio_adapter import LMStudioProviderAdapter
from ai.providers.adapters.local_vision_ocr_adapter import LocalVisionOCRAdapter
from ai.providers.adapters.mock_simulation_adapter import MockSimulationAdapter
from ai.providers.adapters.native_embedding_adapter import NativeEmbeddingAdapter
from ai.providers.adapters.native_gguf_adapter import NativeGGUFAdapter
from ai.providers.adapters.native_reranker_adapter import NativeRerankerAdapter
from ai.providers.adapters.ollama_adapter import OllamaProviderAdapter
from ai.providers.adapters.openai_compatible_adapter import LocalOpenAICompatibleAdapter
from ai.providers.exceptions import (
    AIProviderError,
    ContextOverflowError,
    InputValidationError,
    ModelNotFoundError,
    ProviderCrashedError,
    ProviderModelIncompatibleError,
    ProviderOOMError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from ai.providers.fallback_chain import ProviderFallbackExecutor
from ai.providers.registry import ProviderAdapterRegistry
from ai.registry.models import ModelCapabilityEnum, ModelManifest, ModelTaskTypeEnum
from ai.registry.registry_service import model_registry_service
from ai.retrieval.embedding_provider import DeterministicEmbeddingProvider
from ai.retrieval.reranker_provider import DeterministicCrossEncoderReranker


# =============================================================================
# FIXTURES & HELPERS
# =============================================================================

@pytest.fixture(autouse=True)
def setup_test_manifests():
    """Registers standard test models in ModelRegistry for AI-02 gate checks."""
    manifest_gen = ModelManifest(
        model_id="qwen2.5-3b-active",
        model_name="qwen2.5-3b-instruct",
        display_name="Qwen 2.5 3B Instruct",
        version="1.0.0",
        file_path="models/qwen2.5-3b-instruct.Q4_K_M.gguf",
        file_size_bytes=2_100_000_000,
        sha256_checksum="687635678abcdef0123456789abcdef0123456789abcdef0123456789abcdef0",
        format=ModelFormatEnum.GGUF,
        quantization="Q4_K_M",
        architecture="qwen2",
        parameter_count="3.0B",
        primary_task_type=ModelTaskTypeEnum.GENERATION,
        capabilities=[ModelCapabilityEnum.GENERATION, ModelCapabilityEnum.STRUCTURED_OUTPUT],
        supported_tasks=[TaskType.REASONING, TaskType.GROUNDED_REASONING, TaskType.STRUCTURED_EXTRACTION],
        base_context_length=32768,
        recommended_context_length=4096,
        estimated_weights_vram_mb=2100,
        status=ModelStatusEnum.ACTIVE_REGISTERED,
    )
    manifest_quarantine = ModelManifest(
        model_id="malicious-model-quarantined",
        model_name="malicious-model",
        display_name="Malicious Quarantined Model",
        version="1.0.0",
        file_path="models/malicious.gguf",
        file_size_bytes=1_000_000,
        sha256_checksum="111115678abcdef0123456789abcdef0123456789abcdef0123456789abcdef0",
        format=ModelFormatEnum.GGUF,
        quantization="Q4_K_M",
        architecture="unknown",
        parameter_count="1.0B",
        primary_task_type=ModelTaskTypeEnum.GENERATION,
        capabilities=[ModelCapabilityEnum.GENERATION],
        supported_tasks=[TaskType.REASONING],
        status=ModelStatusEnum.QUARANTINED,
    )
    manifest_embed = ModelManifest(
        model_id="qwen3-embedding-0.6b",
        model_name="qwen3-embedding",
        display_name="Qwen3 Dense Embedding 0.6B",
        version="1.0.0",
        file_path="models/qwen3-embedding.gguf",
        file_size_bytes=600_000_000,
        sha256_checksum="222225678abcdef0123456789abcdef0123456789abcdef0123456789abcdef0",
        format=ModelFormatEnum.GGUF,
        quantization="Q8_0",
        architecture="qwen3",
        parameter_count="0.6B",
        primary_task_type=ModelTaskTypeEnum.EMBEDDING,
        capabilities=[ModelCapabilityEnum.EMBEDDING],
        supported_tasks=[TaskType.EMBEDDING],
        embedding_dimension=384,
        status=ModelStatusEnum.ACTIVE_REGISTERED,
    )

    model_registry_service.register_manifest(manifest_gen, overwrite=True)
    model_registry_service.register_manifest(manifest_quarantine, overwrite=True)
    model_registry_service.register_manifest(manifest_embed, overwrite=True)


# =============================================================================
# 1. BASE CONTRACT & TELEMETRY TESTS
# =============================================================================

def test_01_provider_adapter_contracts_and_types():
    """Verify BaseProviderAdapter protocol, telemetry counters, and properties."""
    adapter = NativeGGUFAdapter()
    assert adapter.provider_type == ProviderTypeEnum.BUILTIN_NATIVE_GGUF
    assert not adapter.is_simulation
    assert TaskType.REASONING in adapter.supported_tasks()

    # Telemetry recording
    adapter.record_success(latency_seconds=0.15, prompt_tokens=100, completion_tokens=50, ttft_ms=45.0)
    assert adapter.telemetry.total_requests == 1
    assert adapter.telemetry.successful_requests == 1
    assert adapter.telemetry.total_prompt_tokens == 100
    assert adapter.telemetry.total_completion_tokens == 50
    assert adapter.telemetry.average_latency_ms == 150.0
    assert adapter.health_status == ProviderHealthStatusEnum.HEALTHY

    adapter.record_failure("Transient failure")
    assert adapter.telemetry.total_requests == 2
    assert adapter.telemetry.failed_requests == 1
    assert adapter.health_status == ProviderHealthStatusEnum.DEGRADED


# =============================================================================
# 2. NATIVE GGUF ADAPTER TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_02_native_gguf_adapter_text_generation_and_metrics():
    """Verify native GGUF generation, streaming, and telemetry updates."""
    adapter = NativeGGUFAdapter()
    text = await adapter.generate_text(
        prompt="Explain cost reduction opportunities for die casting.",
        model_id="qwen2.5-3b-active",
        max_tokens=64,
        temperature=0.0,
    )
    assert isinstance(text, str)
    assert len(text) > 0
    assert adapter.telemetry.successful_requests >= 1

    # Test streaming
    chunks = []
    async for chunk in adapter.stream_chat(
        messages=[{"role": "user", "content": "hello"}],
        model_id="qwen2.5-3b-active",
        max_tokens=10,
    ):
        chunks.append(chunk)
    assert len(chunks) >= 1


def test_03_native_gguf_adapter_error_translation():
    """Verify engine exception mapping to structured AIProviderError subclasses."""
    adapter = NativeGGUFAdapter()

    # OOM
    err_oom = adapter.translate_exception(RuntimeError("CUDA out of memory in llama.cpp"), model_id="test-m")
    assert isinstance(err_oom, ProviderOOMError)
    assert err_oom.error_class == "PROVIDER_OOM"

    # Timeout
    err_to = adapter.translate_exception(asyncio.TimeoutError(), model_id="test-m")
    assert isinstance(err_to, ProviderTimeoutError)
    assert err_to.retryable is True

    # Missing model
    err_mf = adapter.translate_exception(RuntimeError("No model is currently loaded"), model_id="test-m")
    assert isinstance(err_mf, ModelNotFoundError)

    # Crashed
    err_cr = adapter.translate_exception(RuntimeError("Server process terminated"), model_id="test-m")
    assert isinstance(err_cr, ProviderCrashedError)


@pytest.mark.asyncio
async def test_04_native_gguf_adapter_health_probes():
    """Verify passive and active health probes on Native GGUF adapter."""
    adapter = NativeGGUFAdapter()
    passive_rep = await adapter.passive_health_probe()
    assert isinstance(passive_rep, ProviderHealthReport)
    assert passive_rep.probe_type == "PASSIVE"
    assert passive_rep.is_live_verified is True

    active_rep = await adapter.active_health_probe()
    assert isinstance(active_rep, ProviderHealthReport)
    assert active_rep.probe_type == "ACTIVE"


# =============================================================================
# 3. NATIVE EMBEDDING & RERANKER ADAPTERS
# =============================================================================

@pytest.mark.asyncio
async def test_05_native_embedding_adapter_batching_and_norm():
    """Verify native embedding adapter dimension querying, L2 norm, and batch processing."""
    adapter = NativeEmbeddingAdapter()
    assert adapter.get_dimension() == 384
    assert adapter.is_normalized() is True

    texts = ["Alloy casting", "Handlebar weight reduction", "Plant energy audit"]
    vectors = await adapter.embed_texts(texts)
    assert len(vectors) == 3
    assert len(vectors[0]) == 384

    # Empty text handling
    empty_vecs = await adapter.embed_texts([])
    assert empty_vecs == []


@pytest.mark.asyncio
async def test_06_native_reranker_adapter_candidate_ranking():
    """Verify native cross-encoder reranker adapter scoring and ranking."""
    adapter = NativeRerankerAdapter()
    candidates = [
        {"id": "doc1", "text": "Handlebar lightweighting with aluminum 6061", "score": 0.6},
        {"id": "doc2", "text": "Irrelevant cafeteria menu notice", "score": 0.7},
    ]
    results = await adapter.rerank_async(query="Handlebar aluminum", candidates=candidates, top_k=2)
    assert len(results) == 2
    assert results[0]["id"] == "doc1"
    assert results[0]["rerank_score"] >= results[1]["rerank_score"]


# =============================================================================
# 4. OLLAMA LOCAL ADAPTER TESTS (TEST DOUBLES)
# =============================================================================

class MockHTTPResponse:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data

    def decode(self, encoding="utf-8") -> str:
        return self._data.decode(encoding)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __iter__(self):
        for line in self._data.split(b"\n"):
            if line:
                yield line


@pytest.mark.asyncio
async def test_07_ollama_adapter_available_with_test_double():
    """Verify Ollama adapter text generation, passive reachability, and embedding with test double."""
    adapter = OllamaProviderAdapter(base_url="http://127.0.0.1:11434")

    # Mock /api/tags for passive probe
    tags_response = json.dumps({"models": [{"name": "qwen2.5:3b"}, {"name": "qwen3-embedding:0.6b"}]}).encode("utf-8")
    with patch("urllib.request.urlopen", return_value=MockHTTPResponse(tags_response)):
        report = await adapter.passive_health_probe()
        assert report.status == ProviderHealthStatusEnum.HEALTHY
        assert "qwen2.5:3b" in report.available_models
        assert report.is_live_verified is True

    # Mock /api/generate
    gen_response = json.dumps({
        "response": "Feasibility verified for aluminum alloy substitution.",
        "prompt_eval_count": 15,
        "eval_count": 25,
    }).encode("utf-8")
    with patch("urllib.request.urlopen", return_value=MockHTTPResponse(gen_response)):
        text = await adapter.generate_text(prompt="Check feasibility", model_id="qwen2.5:3b")
        assert "Feasibility verified" in text
        assert adapter.telemetry.successful_requests >= 1


@pytest.mark.asyncio
async def test_08_ollama_adapter_unavailable_and_error_translation():
    """Verify Ollama adapter handles daemon connection refusal without unhandled crashes."""
    adapter = OllamaProviderAdapter(base_url="http://127.0.0.1:11434")

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        report = await adapter.passive_health_probe()
        assert report.status == ProviderHealthStatusEnum.OFFLINE
        assert report.is_live_verified is False

        with pytest.raises(ProviderUnavailableError) as exc_info:
            await adapter.generate_text(prompt="ping", model_id="qwen2.5:3b")
        assert "unavailable" in exc_info.value.message.lower()


# =============================================================================
# 5. LM STUDIO LOCAL ADAPTER TESTS (TEST DOUBLES)
# =============================================================================

@pytest.mark.asyncio
async def test_09_lm_studio_adapter_available_with_test_double():
    """Verify LM Studio adapter /v1/chat/completions and /v1/models using test doubles."""
    adapter = LMStudioProviderAdapter(base_url="http://127.0.0.1:1234")

    # Mock /v1/models
    models_resp = json.dumps({"data": [{"id": "qwen2.5-3b-instruct"}]}).encode("utf-8")
    with patch("urllib.request.urlopen", return_value=MockHTTPResponse(models_resp)):
        report = await adapter.passive_health_probe()
        assert report.status == ProviderHealthStatusEnum.HEALTHY
        assert "qwen2.5-3b-instruct" in report.available_models

    # Mock /v1/chat/completions
    chat_resp = json.dumps({
        "choices": [{"message": {"content": "LM Studio generated response for cost review."}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 18},
    }).encode("utf-8")
    with patch("urllib.request.urlopen", return_value=MockHTTPResponse(chat_resp)):
        res = await adapter.generate_text(prompt="Cost review", model_id="qwen2.5-3b-instruct")
        assert "LM Studio" in res


@pytest.mark.asyncio
async def test_10_lm_studio_adapter_unavailable_and_error_translation():
    """Verify LM Studio adapter translates connection failures into ProviderUnavailableError."""
    adapter = LMStudioProviderAdapter(base_url="http://127.0.0.1:1234")

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
        with pytest.raises(ProviderUnavailableError) as exc_info:
            await adapter.generate_text(prompt="hello", model_id="qwen2.5-3b-instruct")
        assert exc_info.value.error_class == "PROVIDER_UNAVAILABLE"


# =============================================================================
# 6. LOCAL OPENAI-COMPATIBLE & VISION/OCR CONTRACTS
# =============================================================================

@pytest.mark.asyncio
async def test_11_openai_compatible_adapter_available_and_error_handling():
    """Verify generic local OpenAI-compatible adapter."""
    adapter = LocalOpenAICompatibleAdapter(base_url="http://127.0.0.1:8000")
    assert TaskType.REASONING in adapter.supported_tasks()

    chat_resp = json.dumps({
        "choices": [{"message": {"content": "Local OpenAI-compatible engine response."}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10},
    }).encode("utf-8")
    with patch("urllib.request.urlopen", return_value=MockHTTPResponse(chat_resp)):
        text = await adapter.generate_text(prompt="Analyze", model_id="local-model")
        assert "Local OpenAI-compatible" in text


@pytest.mark.asyncio
async def test_12_local_vision_ocr_adapter_contract_baseline():
    """Verify VisionOCRAdapter contract baseline and graceful unconfigured response."""
    adapter = LocalVisionOCRAdapter(is_configured=False)
    assert adapter.supported_tasks() == [TaskType.VISION_OCR]

    # Passive health report indicates phase note
    report = await adapter.passive_health_probe()
    assert report.status == ProviderHealthStatusEnum.OFFLINE
    assert "AI-15" in report.details.get("phase_note", "")

    # Invoking unconfigured vision engine raises ModelNotFoundError
    with pytest.raises(ModelNotFoundError):
        await adapter.extract_text(document_bytes=b"dummy_image_data", mime_type="image/png")

    # Empty bytes triggers InputValidationError
    with pytest.raises(InputValidationError):
        await adapter.extract_text(document_bytes=b"", mime_type="image/png")


# =============================================================================
# 7. MOCK PROVIDER ISOLATION
# =============================================================================

def test_13_mock_simulation_adapter_isolated_and_explicit():
    """Verify MockSimulationAdapter is strictly marked as simulation."""
    adapter = MockSimulationAdapter()
    assert adapter.is_simulation is True
    assert adapter.provider_type == ProviderTypeEnum.MOCK_SIMULATION


# =============================================================================
# 8. PROVIDER ADAPTER REGISTRY
# =============================================================================

@pytest.mark.asyncio
async def test_14_provider_adapter_registry_lifecycle_and_discovery():
    """Verify ProviderAdapterRegistry registration, task capability discovery, and health summary."""
    registry = ProviderAdapterRegistry(register_defaults=True)

    adapters = registry.list_adapters()
    assert len(adapters) >= 5

    reasoning_adapters = registry.discover_adapters_for_task(TaskType.REASONING)
    assert len(reasoning_adapters) >= 3  # Native, Ollama, LM Studio, etc.

    embedding_adapters = registry.discover_adapters_for_task(TaskType.EMBEDDING)
    assert len(embedding_adapters) >= 1

    # Dynamic registration and unregistration
    custom_mock = MockSimulationAdapter(name="custom-test-double")
    registry.register_adapter(custom_mock)
    assert registry.get_adapter("custom-test-double") is not None

    removed = registry.unregister_adapter("custom-test-double")
    assert removed is True
    assert registry.get_adapter("custom-test-double") is None

    # Health summary
    summary = await registry.get_health_summary(active_probe=False)
    assert "builtin-native-gguf" in summary
    assert summary["builtin-native-gguf"].status == ProviderHealthStatusEnum.HEALTHY


# =============================================================================
# 9. POLICY-DRIVEN FALLBACK & NO SILENT FALLBACK
# =============================================================================

@pytest.mark.asyncio
async def test_15_provider_fallback_chain_primary_success():
    """Verify transparent execution when primary provider succeeds without fallback."""
    executor = ProviderFallbackExecutor()
    policy = FallbackPolicy(allow_provider_fallback=False)

    text, record = await executor.execute_text_generation(
        prompt="Synthesize BOM variance",
        model_id="qwen2.5-3b-active",
        task_type=TaskType.REASONING,
        policy_override=policy,
    )
    assert isinstance(text, str)
    assert record.fallback_occurred is False
    assert record.requested_provider == "BUILTIN_NATIVE_GGUF"
    assert record.actual_provider == "builtin-native-gguf"
    assert record.is_simulation is False


@pytest.mark.asyncio
async def test_16_provider_fallback_chain_failover_when_policy_allows():
    """Verify fallback executes and logs failover provenance when allow_provider_fallback=True."""
    registry = ProviderAdapterRegistry(register_defaults=False)
    # Create failing primary and working fallback
    primary_bad = LMStudioProviderAdapter(name="bad-lm-studio", base_url="http://127.0.0.1:9999")
    fallback_good = NativeGGUFAdapter(name="fallback-native-gguf")
    registry.register_adapter(primary_bad)
    registry.register_adapter(fallback_good)

    executor = ProviderFallbackExecutor(registry=registry)
    policy = FallbackPolicy(
        allow_provider_fallback=True,
        task_fallback_chains={"REASONING": ["bad-lm-studio", "fallback-native-gguf"]},
    )

    text, record = await executor.execute_text_generation(
        prompt="Analyze opportunity",
        model_id="qwen2.5-3b-active",
        requested_provider="bad-lm-studio",
        policy_override=policy,
    )
    assert record.fallback_occurred is True
    assert record.requested_provider == "bad-lm-studio"
    assert record.actual_provider == "fallback-native-gguf"
    assert "bad-lm-studio" in record.fallback_chain
    assert record.fallback_reason is not None


@pytest.mark.asyncio
async def test_17_no_silent_fallback_when_policy_denies():
    """Verify that if allow_provider_fallback=False, failure in requested provider raises error immediately."""
    registry = ProviderAdapterRegistry(register_defaults=False)
    bad_ollama = OllamaProviderAdapter(name="failing-ollama", base_url="http://127.0.0.1:9999")
    backup_gguf = NativeGGUFAdapter(name="backup-gguf")
    registry.register_adapter(bad_ollama)
    registry.register_adapter(backup_gguf)

    executor = ProviderFallbackExecutor(registry=registry)
    strict_policy = FallbackPolicy(allow_provider_fallback=False)

    with pytest.raises(ProviderUnavailableError):
        await executor.execute_text_generation(
            prompt="Analyze opportunity",
            model_id="qwen2.5-3b-active",
            requested_provider="failing-ollama",
            policy_override=strict_policy,
        )


# =============================================================================
# 10. AI-02 MODEL REGISTRY & AI-03 HARDWARE FIT GATE PRESERVATION
# =============================================================================

@pytest.mark.asyncio
async def test_18_model_registry_and_hardware_fit_gate_preservation():
    """Verify that unverified or quarantined models cannot be executed via any provider adapter."""
    executor = ProviderFallbackExecutor()

    # 1. Unregistered model rejection
    with pytest.raises(AIProviderError) as exc_unreg:
        await executor.execute_text_generation(
            prompt="Test",
            model_id="unregistered-mystery-model",
            task_type=TaskType.REASONING,
        )
    assert "not found in AI-02 Model Registry" in exc_unreg.value.message

    # 2. Quarantined model rejection
    with pytest.raises(AIProviderError) as exc_quarantine:
        await executor.execute_text_generation(
            prompt="Test",
            model_id="malicious-model-quarantined",
            task_type=TaskType.REASONING,
        )
    assert "QUARANTINED" in exc_quarantine.value.message


# =============================================================================
# 11. TASK-SPECIFIC EMBEDDING & RERANKING FALLBACKS
# =============================================================================

@pytest.mark.asyncio
async def test_19_task_specific_embedding_and_reranker_fallback():
    """Verify task-specific execution across embedding and reranking provider chains."""
    executor = ProviderFallbackExecutor()

    # Embedding execution
    vectors, embed_record = await executor.execute_embeddings(
        texts=["Plant casting savings", "Electricity tariff variance"],
        model_id="qwen3-embedding-0.6b",
    )
    assert len(vectors) == 2
    assert embed_record.requested_provider == "BUILTIN_NATIVE_EMBEDDING"
    assert embed_record.is_simulation is False

    # Reranker execution
    results, rerank_record = await executor.execute_reranking(
        query="casting",
        candidates=[{"id": "1", "text": "alloy casting", "score": 0.8}],
        model_id="bge-reranker-v2-m3",
    )
    assert len(results) == 1
    assert rerank_record.requested_provider == "BUILTIN_NATIVE_RERANKER"


def test_20_health_state_transitions_on_consecutive_failures():
    """Verify adapter state transitions: HEALTHY -> DEGRADED -> UNHEALTHY on repeated failures."""
    adapter = NativeGGUFAdapter(name="test-health-adapter")
    assert adapter.health_status == ProviderHealthStatusEnum.OFFLINE

    adapter.record_success(latency_seconds=0.01)
    assert adapter.health_status == ProviderHealthStatusEnum.HEALTHY

    adapter.record_failure("error 1")
    assert adapter.health_status == ProviderHealthStatusEnum.DEGRADED

    adapter.record_failure("error 2")
    assert adapter.health_status == ProviderHealthStatusEnum.DEGRADED

    adapter.record_failure("error 3")
    assert adapter.health_status == ProviderHealthStatusEnum.UNHEALTHY
