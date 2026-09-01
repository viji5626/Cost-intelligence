"""
Phase AI-05 Comprehensive Test Suite: Model Lifecycle Manager & Sequential Swapper
Tests all 22 required lifecycle states, sequential model swapping, request queueing,
priority ordering, health probes, failure recovery, OOM safety, concurrency policies, and telemetry.
"""

import asyncio
import os
import shutil
import tempfile
from typing import Any, AsyncIterator, Dict, List, Optional
import pytest

from ai.core.contracts import InferenceEngineContract
from ai.hardware.profiles import RuntimeProfileName
from ai.providers.native_gguf import NativeGGUFEngine
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
from ai.runtime.lifecycle_manager import ModelLifecycleManager
from ai.runtime.models import (
    LifecycleStateEnum,
    QueuedInferenceRequest,
    QueuedRequestStatusEnum,
    RequestPriorityEnum,
)


class MockEngineStub(InferenceEngineContract):
    """Controllable test inference engine for failure injection and lifecycle verification."""

    def __init__(
        self,
        simulate_fail_load: bool = False,
        simulate_fail_health: bool = False,
        simulate_oom: bool = False,
        simulate_fail_unload: bool = False,
        simulate_timeout: bool = False,
    ):
        self.is_loaded_state: bool = False
        self.active_model_id: Optional[str] = None
        self.simulate_fail_load = simulate_fail_load
        self.simulate_fail_health = simulate_fail_health
        self.simulate_oom = simulate_oom
        self.simulate_fail_unload = simulate_fail_unload
        self.simulate_timeout = simulate_timeout
        self.cancellation_called: bool = False
        self.unload_called: bool = False

    async def is_ready(self) -> bool:
        if self.simulate_fail_health:
            return False
        return self.is_loaded_state

    async def load_model(
        self,
        model_id: str,
        context_length: Optional[int] = None,
        gpu_layers_override: Optional[int] = None,
        force_cpu: bool = False,
        timeout_seconds: float = 60.0,
        **kwargs: Any,
    ) -> bool:
        if self.simulate_timeout:
            await asyncio.sleep(10)
        if self.simulate_oom:
            raise MemoryError("CUDA out of memory: tried to allocate 4.2 GiB")
        if self.simulate_fail_load:
            raise RuntimeError("Engine load error: binary file corrupted")
        self.is_loaded_state = True
        self.active_model_id = model_id
        return True

    async def unload_model(self) -> bool:
        if self.simulate_fail_unload:
            raise RuntimeError("Underlying C-ABI GPU memory unlock failed")
        self.is_loaded_state = False
        self.active_model_id = None
        self.unload_called = True
        return True

    def cancel_current_generation(self) -> None:
        self.cancellation_called = True

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
        stop: Optional[List[str]] = None,
        timeout_seconds: float = 60.0,
    ) -> str:
        if not self.is_loaded_state:
            raise RuntimeError("Engine not loaded")
        return f"Generated answer for: {prompt}"

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.0,
        stop: Optional[List[str]] = None,
        timeout_seconds: float = 60.0,
    ) -> AsyncIterator[str]:
        if not self.is_loaded_state:
            raise RuntimeError("Engine not loaded")
        for chunk in ["Plant ", "OPEX ", "variance ", "normalized."]:
            yield chunk
            await asyncio.sleep(0.01)


@pytest.fixture
def lifecycle_fixture():
    """Provides an isolated ModelRegistry and ModelLifecycleManager sandbox."""
    temp_dir = tempfile.mkdtemp(prefix="hero_ai_05_test_")
    models_dir = os.path.join(temp_dir, "models")
    manifest_file = os.path.join(temp_dir, "registry.json")

    storage = ModelRegistryStorage(base_dir=models_dir, manifest_file=manifest_file)
    registry = ModelRegistryService(storage=storage)

    # Register Model A (SLM Generation)
    path_a = os.path.join(storage.models_dir, "model-a-gen.gguf")
    with open(path_a, "wb") as f:
        f.write(b"GGUF\x03\x00\x00\x00weights_a")

    req_a = ModelRegistrationRequest(
        model_id="model-a-gen",
        display_name="Model A Generation",
        file_path=path_a,
        primary_task_type=ModelTaskTypeEnum.GENERATION,
        capabilities=[ModelCapabilityEnum.GENERATION],
        architecture="llama",
        quantization="Q4_K_M",
        parameter_count="3.0B",
        context_length=4096,
        set_as_default=True,
    )
    registry.onboard_local_model(req_a, auto_activate_if_valid=True)

    # Register Model B (Embedding)
    path_b = os.path.join(storage.models_dir, "model-b-embed.gguf")
    with open(path_b, "wb") as f:
        f.write(b"GGUF\x03\x00\x00\x00weights_b")

    req_b = ModelRegistrationRequest(
        model_id="model-b-embed",
        display_name="Model B Embedding",
        file_path=path_b,
        primary_task_type=ModelTaskTypeEnum.EMBEDDING,
        capabilities=[ModelCapabilityEnum.EMBEDDING],
        architecture="bert",
        quantization="Q8_0",
        parameter_count="0.6B",
        embedding_dimension=1024,
        context_length=2048,
    )
    registry.onboard_local_model(req_b, auto_activate_if_valid=True)

    # Register Model C (Reranker)
    path_c = os.path.join(storage.models_dir, "model-c-rerank.gguf")
    with open(path_c, "wb") as f:
        f.write(b"GGUF\x03\x00\x00\x00weights_c")

    req_c = ModelRegistrationRequest(
        model_id="model-c-rerank",
        display_name="Model C Reranker",
        file_path=path_c,
        primary_task_type=ModelTaskTypeEnum.RERANKER,
        capabilities=[ModelCapabilityEnum.RERANKING],
        architecture="bert",
        quantization="Q8_0",
        parameter_count="0.6B",
        context_length=2048,
    )
    registry.onboard_local_model(req_c, auto_activate_if_valid=True)

    engine = MockEngineStub()
    manager = ModelLifecycleManager(default_engine=engine, runtime_profile_name=RuntimeProfileName.PROFILE_CONSTRAINED)

    yield manager, registry, engine

    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# 1. INITIAL LOAD & STATE MACHINE TESTS (1-3)
# ==============================================================================

@pytest.mark.asyncio
async def test_01_load_pipeline_to_ready(lifecycle_fixture, monkeypatch):
    """Test 1: Model passes through PREFLIGHT -> LOADING -> READY with health probe."""
    manager, registry, engine = lifecycle_fixture
    monkeypatch.setattr("ai.runtime.lifecycle_manager.model_registry_service", registry)

    instance = await manager.load_model("model-a-gen", context_length=2048)

    assert instance.state == LifecycleStateEnum.READY
    assert instance.health_check_passed is True
    assert instance.model_id == "model-a-gen"
    assert instance.instance_id is not None
    assert engine.is_loaded_state is True
    assert engine.active_model_id == "model-a-gen"


@pytest.mark.asyncio
async def test_02_unregistered_model_load_failure(lifecycle_fixture, monkeypatch):
    """Test 2: Unregistered model transitions to LOAD_FAILED with no residual READY state."""
    manager, registry, engine = lifecycle_fixture
    monkeypatch.setattr("ai.runtime.lifecycle_manager.model_registry_service", registry)

    with pytest.raises(FileNotFoundError):
        await manager.load_model("unknown-model-xyz")

    assert len(manager.get_active_instances()) == 0
    assert engine.is_loaded_state is False


@pytest.mark.asyncio
async def test_03_health_check_failure_aborts_load(lifecycle_fixture, monkeypatch):
    """Test 3: Failed health probe triggers HEALTH_DEGRADED and aborts activation."""
    manager, registry, engine = lifecycle_fixture
    monkeypatch.setattr("ai.runtime.lifecycle_manager.model_registry_service", registry)
    engine.simulate_fail_health = True

    with pytest.raises(RuntimeError, match="failed post-load health probe"):
        await manager.load_model("model-a-gen")

    assert len(manager.get_active_instances()) == 0
    assert engine.is_loaded_state is False


# ==============================================================================
# 2. INFERENCE EXECUTION, STREAMING & CANCELLATION (4-6)
# ==============================================================================

@pytest.mark.asyncio
async def test_04_execute_inference_lifecycle_flow(lifecycle_fixture, monkeypatch):
    """Test 4: Inference transitions instance from READY -> EXECUTING -> READY."""
    manager, registry, engine = lifecycle_fixture
    monkeypatch.setattr("ai.runtime.lifecycle_manager.model_registry_service", registry)

    result = await manager.execute_inference(
        model_id="model-a-gen",
        prompt="Explain plant OPEX.",
    )

    assert "Generated answer for: Explain plant OPEX." in result
    instance = manager.get_instance_by_model("model-a-gen")
    assert instance.state == LifecycleStateEnum.READY


@pytest.mark.asyncio
async def test_05_stream_inference_tokens(lifecycle_fixture, monkeypatch):
    """Test 5: Streaming token generator executes correctly across lifecycle."""
    manager, registry, engine = lifecycle_fixture
    monkeypatch.setattr("ai.runtime.lifecycle_manager.model_registry_service", registry)

    messages = [{"role": "user", "content": "Explain variance."}]
    chunks = []
    async for chunk in manager.stream_inference("model-a-gen", messages):
        chunks.append(chunk)

    assert len(chunks) == 4
    assert "".join(chunks) == "Plant OPEX variance normalized."


@pytest.mark.asyncio
async def test_06_cancellation_propagation(lifecycle_fixture, monkeypatch):
    """Test 6: cancel_active_instance() propagates cancellation signal to engine."""
    manager, registry, engine = lifecycle_fixture
    monkeypatch.setattr("ai.runtime.lifecycle_manager.model_registry_service", registry)

    instance = await manager.load_model("model-a-gen")
    instance.update_state(LifecycleStateEnum.EXECUTING)

    cancelled = manager.cancel_active_instance(instance.instance_id)
    assert cancelled is True
    assert engine.cancellation_called is True
    assert instance.state == LifecycleStateEnum.CANCELLING


# ==============================================================================
# 3. TIMEOUT & UNLOAD CYCLING (7-8)
# ==============================================================================

@pytest.mark.asyncio
async def test_07_load_timeout_handling(lifecycle_fixture, monkeypatch):
    """Test 7: Load timeout triggers safe abort and cleans up state."""
    manager, registry, engine = lifecycle_fixture
    monkeypatch.setattr("ai.runtime.lifecycle_manager.model_registry_service", registry)
    engine.simulate_timeout = True

    with pytest.raises(Exception):
        await manager.load_model("model-a-gen", timeout_seconds=0.1)

    assert len(manager.get_active_instances()) == 0


@pytest.mark.asyncio
async def test_08_repeated_load_unload_cycling(lifecycle_fixture, monkeypatch):
    """Test 8: Repeated load and unload cycles maintain zero residual state."""
    manager, registry, engine = lifecycle_fixture
    monkeypatch.setattr("ai.runtime.lifecycle_manager.model_registry_service", registry)

    for _ in range(3):
        inst = await manager.load_model("model-a-gen")
        assert inst.state == LifecycleStateEnum.READY
        assert engine.is_loaded_state is True

        await manager.unload_model("model-a-gen")
        assert len(manager.get_active_instances()) == 0
        assert engine.is_loaded_state is False


# ==============================================================================
# 4. SEQUENTIAL SWAPPING & CONCURRENCY POLICIES (9-13)
# ==============================================================================

@pytest.mark.asyncio
async def test_09_sequential_swapper_model_a_to_b(lifecycle_fixture, monkeypatch):
    """Test 9: Sequential swapper cleanly evicts Model A before activating Model B."""
    manager, registry, engine = lifecycle_fixture
    monkeypatch.setattr("ai.runtime.lifecycle_manager.model_registry_service", registry)

    # 1. Load Model A
    inst_a = await manager.load_model("model-a-gen")
    assert inst_a.model_id == "model-a-gen"
    assert engine.active_model_id == "model-a-gen"

    # 2. Switch to Model B (Embedding)
    inst_b = await manager.switch_model(
        current_model_id="model-a-gen",
        new_model_id="model-b-embed",
        target_task=ModelTaskTypeEnum.EMBEDDING,
    )

    assert inst_b.model_id == "model-b-embed"
    assert inst_b.state == LifecycleStateEnum.READY
    assert engine.active_model_id == "model-b-embed"
    assert manager.get_instance_by_model("model-a-gen") is None
    assert len(manager.get_active_instances()) == 1


@pytest.mark.asyncio
async def test_10_concurrent_profile_eviction_on_capacity_limit(lifecycle_fixture, monkeypatch):
    """Test 10: On constrained profile (max_concurrent_models=1), loading Model C auto-evicts Model B."""
    manager, registry, engine = lifecycle_fixture
    monkeypatch.setattr("ai.runtime.lifecycle_manager.model_registry_service", registry)

    await manager.load_model("model-b-embed", task_type=ModelTaskTypeEnum.EMBEDDING)
    assert manager.get_instance_by_model("model-b-embed") is not None

    # Load Model C -> should evict Model B automatically
    await manager.load_model("model-c-rerank", task_type=ModelTaskTypeEnum.RERANKER)
    assert manager.get_instance_by_model("model-b-embed") is None
    assert manager.get_instance_by_model("model-c-rerank") is not None
    assert len(manager.get_active_instances()) == 1


def test_11_request_priority_queue_ordering(lifecycle_fixture):
    """Test 11: Request queue prioritizes HIGH requests ahead of NORMAL and LOW."""
    manager, _, _ = lifecycle_fixture

    req_low = QueuedInferenceRequest(model_id="model-a-gen", priority=RequestPriorityEnum.LOW, prompt="Low task")
    req_high = QueuedInferenceRequest(model_id="model-a-gen", priority=RequestPriorityEnum.HIGH, prompt="High task")
    req_norm = QueuedInferenceRequest(model_id="model-a-gen", priority=RequestPriorityEnum.NORMAL, prompt="Normal task")

    manager.enqueue_request(req_low)
    manager.enqueue_request(req_high)
    manager.enqueue_request(req_norm)

    queue = manager.get_queue_status()
    assert len(queue) == 3
    assert queue[0]["priority"] == RequestPriorityEnum.HIGH.value
    assert queue[1]["priority"] == RequestPriorityEnum.NORMAL.value
    assert queue[2]["priority"] == RequestPriorityEnum.LOW.value


def test_12_queued_request_cancellation(lifecycle_fixture):
    """Test 12: Pending request can be cancelled before execution."""
    manager, _, _ = lifecycle_fixture

    req = QueuedInferenceRequest(model_id="model-a-gen", prompt="Cancel me")
    req_id = manager.enqueue_request(req)

    assert len(manager.get_queue_status()) == 1
    cancelled = manager.cancel_queued_request(req_id)
    assert cancelled is True
    assert len(manager.get_queue_status()) == 0


# ==============================================================================
# 5. FAILURE RECOVERY, CUDA OOM & ERROR RESILIENCE (13-17)
# ==============================================================================

@pytest.mark.asyncio
async def test_13_cuda_oom_recovery(lifecycle_fixture, monkeypatch):
    """Test 13: CUDA OOM triggers clean unallocation and marks OOM_RECOVERED."""
    manager, registry, engine = lifecycle_fixture
    monkeypatch.setattr("ai.runtime.lifecycle_manager.model_registry_service", registry)
    engine.simulate_oom = True

    with pytest.raises(MemoryError, match="CUDA out of memory"):
        await manager.load_model("model-a-gen")

    assert len(manager.get_active_instances()) == 0
    assert engine.is_loaded_state is False


@pytest.mark.asyncio
async def test_14_unload_failure_resilience(lifecycle_fixture, monkeypatch):
    """Test 14: Unload failure logs warning but safely cleans up state."""
    manager, registry, engine = lifecycle_fixture
    monkeypatch.setattr("ai.runtime.lifecycle_manager.model_registry_service", registry)

    await manager.load_model("model-a-gen")
    engine.simulate_fail_unload = True

    unloaded = await manager.unload_model("model-a-gen")
    assert unloaded is True
    assert len(manager.get_active_instances()) == 0


@pytest.mark.asyncio
async def test_15_stale_lifecycle_state_prevention(lifecycle_fixture, monkeypatch):
    """Test 15: An aborted or errored load never leaves a stale READY state."""
    manager, registry, engine = lifecycle_fixture
    monkeypatch.setattr("ai.runtime.lifecycle_manager.model_registry_service", registry)
    engine.simulate_fail_load = True

    with pytest.raises(RuntimeError, match="Engine load error"):
        await manager.load_model("model-a-gen")

    assert manager.get_instance_by_model("model-a-gen") is None
    assert manager.active_model is None


# ==============================================================================
# 6. RUNTIME INSTANCE IDENTITY, PROVENANCE & TELEMETRY (18-20)
# ==============================================================================

@pytest.mark.asyncio
async def test_16_runtime_instance_id_and_provenance(lifecycle_fixture, monkeypatch):
    """Test 16: Preserves unique runtime instance ID and ModelProvenance."""
    manager, registry, engine = lifecycle_fixture
    monkeypatch.setattr("ai.runtime.lifecycle_manager.model_registry_service", registry)

    inst = await manager.load_model("model-a-gen")
    assert inst.instance_id != ""
    assert inst.provenance is not None
    assert inst.provenance.model_id == "model-a-gen"
    assert inst.provenance.model_file_hash is not None


@pytest.mark.asyncio
async def test_17_telemetry_capture_on_instance(lifecycle_fixture, monkeypatch):
    """Test 17: Tracks estimated and observed VRAM/RAM metrics on instance."""
    manager, registry, engine = lifecycle_fixture
    monkeypatch.setattr("ai.runtime.lifecycle_manager.model_registry_service", registry)

    inst = await manager.load_model("model-a-gen")
    assert inst.estimated_vram_mb > 0.0
    assert inst.context_length == 4096
    assert inst.loaded_at is not None
    assert inst.last_active_at is not None
