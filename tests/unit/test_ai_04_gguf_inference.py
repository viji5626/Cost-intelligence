"""
Phase AI-04 Test Suite: Native GGUF Inference Core
Tests model loading, hardware fit admission, token generation, streaming, cancellation, timeouts, and telemetry.
"""

import asyncio
import os
import shutil
import tempfile
import pytest

from ai.core.contracts import TaskType
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


@pytest.fixture
def temp_ai_runtime():
    """Sets up an isolated test sandbox for model registry and GGUF engine."""
    temp_dir = tempfile.mkdtemp(prefix="hero_ai_04_test_")
    models_dir = os.path.join(temp_dir, "models")
    manifest_file = os.path.join(temp_dir, "registry.json")

    storage = ModelRegistryStorage(base_dir=models_dir, manifest_file=manifest_file)
    registry = ModelRegistryService(storage=storage)
    engine = NativeGGUFEngine()

    # Create synthetic GGUF model
    gguf_path = os.path.join(storage.models_dir, "qwen2.5-3b-test.gguf")
    with open(gguf_path, "wb") as f:
        f.write(b"GGUF\x03\x00\x00\x00synthetic_test_weights")

    req = ModelRegistrationRequest(
        model_id="qwen2.5-3b-test",
        display_name="Qwen 2.5 3B Test GGUF",
        file_path=gguf_path,
        primary_task_type=ModelTaskTypeEnum.GENERATION,
        capabilities=[ModelCapabilityEnum.GENERATION, ModelCapabilityEnum.STRUCTURED_OUTPUT],
        architecture="qwen2.5-3b",
        quantization="Q4_K_M",
        parameter_count="3.09B",
        context_length=4096,
        set_as_default=True,
    )
    registry.onboard_local_model(req, auto_activate_if_valid=True)

    yield engine, registry, "qwen2.5-3b-test"

    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# 1. ADMISSION CONTROL & MODEL LOADING TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_unregistered_model_load_fails(temp_ai_runtime):
    """Test: Attempting to load an unregistered model raises FileNotFoundError."""
    engine, registry, _ = temp_ai_runtime
    with pytest.raises(FileNotFoundError):
        await engine.load_model("nonexistent-model-id")


@pytest.mark.asyncio
async def test_quarantined_model_load_denied(temp_ai_runtime, monkeypatch):
    """Test: Model in QUARANTINED state cannot be loaded until activated."""
    engine, registry, model_id = temp_ai_runtime
    registry.quarantine_model(model_id, "Security review needed")

    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    with pytest.raises(PermissionError, match="ACTIVE_REGISTERED"):
        await engine.load_model(model_id)


@pytest.mark.asyncio
async def test_valid_model_load_and_unload(temp_ai_runtime, monkeypatch):
    """Test: Valid model loads successfully and measures telemetry baseline."""
    engine, registry, model_id = temp_ai_runtime

    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)

    # 1. Load
    loaded = await engine.load_model(model_id, context_length=2048)
    assert loaded is True
    assert engine.is_loaded is True
    assert engine.active_manifest.model_id == model_id
    assert engine.metrics.load_duration_seconds >= 0.0

    # 2. Unload
    unloaded = await engine.unload_model()
    assert unloaded is True
    assert engine.is_loaded is False
    assert engine.active_manifest is None


# ==============================================================================
# 2. GENERATION & STREAMING TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_actual_text_generation(temp_ai_runtime, monkeypatch):
    """Test: Executes generation for OPEX query and validates response."""
    engine, registry, model_id = temp_ai_runtime

    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    prompt = "Explain in one sentence why plant OPEX is benchmarked per vehicle."
    response = await engine.generate_text(prompt, max_tokens=100)

    assert response != ""
    assert "Plant OPEX is benchmarked per vehicle" in response
    assert engine.metrics.total_tokens_generated > 0
    assert engine.metrics.generation_tokens_per_sec > 0.0


@pytest.mark.asyncio
async def test_streaming_token_generation(temp_ai_runtime, monkeypatch):
    """Test: Streams tokens iteratively through async generator."""
    engine, registry, model_id = temp_ai_runtime

    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    tokens = []
    messages = [{"role": "user", "content": "Explain why volume normalization matters."}]
    async for tok in engine.stream_chat(messages):
        tokens.append(tok)

    assert len(tokens) > 5
    full_text = "".join(tokens)
    assert "Operational metrics require volume normalization" in full_text


# ==============================================================================
# 3. CANCELLATION & TIMEOUT TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_streaming_cancellation(temp_ai_runtime, monkeypatch):
    """Test: Calling cancel_current_generation() aborts streaming generator cleanly."""
    engine, registry, model_id = temp_ai_runtime

    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    tokens_received = 0
    messages = [{"role": "user", "content": "Explain why plant OPEX is benchmarked per vehicle."}]

    async for tok in engine.stream_chat(messages):
        tokens_received += 1
        if tokens_received == 3:
            engine.cancel_current_generation()  # Trigger cancel after 3 tokens

    # Ensure generation halted early
    assert tokens_received < 15


# ==============================================================================
# 4. EXECUTION ENVELOPE & PROVENANCE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_execution_envelope_provenance(temp_ai_runtime, monkeypatch):
    """Test: Wraps inference in AIExecutionEnvelope with valid provenance and audit hash."""
    engine, registry, model_id = temp_ai_runtime

    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    res_text = await engine.generate_text("Explain why volume normalization is critical.")
    envelope = engine.create_execution_envelope(
        task_id="task-eval-001",
        result_text=res_text,
        grounding_score=0.95,
    )

    assert envelope.task_id == "task-eval-001"
    assert envelope.task_type == TaskType.REASONING
    assert envelope.provenance.model_id == model_id
    assert len(envelope.audit_hash) == 64
    assert envelope.grounding_score == 0.95
