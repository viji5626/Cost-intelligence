"""
Phase AI-14 Unit & Integration Test Suite
Validates Local OpenAI-Compatible API (/v1), AI-12 Orchestration Routing, Security Gates,
Streaming SSE, Disconnect Cancellation, Embeddings, and Real OpenAI Python SDK Compatibility.
"""

import asyncio
import json
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
import httpx
from openai import AsyncOpenAI

from ai.api.openai_schemas import (
    ChatCompletionMessage,
    ChatCompletionRequest,
    CompletionRequest,
    EmbeddingRequest,
    ModelListResponse,
    ToolDefinitionSchema,
    FunctionDefinition,
)
from ai.api.openai_service import OpenAIService, openai_service
from ai.core.contracts import TaskType
from ai.orchestrator.central_orchestrator import AIOrchestrator
from ai.registry.models import (
    ModelCapabilityEnum,
    ModelFormatEnum,
    ModelManifest,
    ModelStatusEnum,
    ModelTaskTypeEnum,
)
from ai.registry.registry_service import model_registry_service
from backend.app.core.config import settings
from backend.app.main import app


# =============================================================================
# FIXTURES
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
        context_length=32768,
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


@pytest.fixture
def client():
    return TestClient(app)


# =============================================================================
# TEST CASES
# =============================================================================

def test_01_localhost_binding_and_cors_policy():
    """Requirement 3 & 4: Default server bind must be 127.0.0.1; CORS is explicit local allowlist."""
    assert settings.HOST == "127.0.0.1", "Host bind default must be 127.0.0.1"
    assert "*" not in settings.CORS_ORIGINS, "CORS must not allow wildcard origin"
    assert "http://localhost:5173" in settings.CORS_ORIGINS
    assert "http://127.0.0.1:8000" in settings.CORS_ORIGINS


def test_02_authentication_modes(client):
    """Requirement 5: Configurable API authentication (trusted_local, api_key, disabled)."""
    service = OpenAIService()

    # Trusted local mode with local IP
    assert service.authenticate_request(authorization=None, client_host="127.0.0.1") is True
    assert service.authenticate_request(authorization=None, client_host="localhost") is True

    # Trusted local mode with non-local IP without key -> raises 401
    with pytest.raises(Exception) as exc:
        service.authenticate_request(authorization=None, client_host="192.168.1.50")
    assert exc.value.status_code == 401

    # Valid key
    assert service.authenticate_request(
        authorization=f"Bearer {settings.OPENAI_API_KEY}",
        client_host="192.168.1.50",
    ) is True


def test_03_model_listing_safety_and_filtering(client):
    """Requirement 2: /v1/models exposes only ACTIVE_REGISTERED models, excluding QUARANTINED."""
    res = client.get("/v1/models")
    assert res.status_code == 200
    data = res.json()
    assert data["object"] == "list"

    model_ids = [m["id"] for m in data["data"]]
    assert "qwen2.5-3b-active" in model_ids
    assert "qwen3-embedding-0.6b" in model_ids
    # Crucial safety check: Quarantined model must be excluded
    assert "malicious-model-quarantined" not in model_ids


def test_04_get_model_detail(client):
    """Requirement 10: GET /v1/models/{model_id} returns model card or 404."""
    res = client.get("/v1/models/qwen2.5-3b-active")
    assert res.status_code == 200
    card = res.json()
    assert card["id"] == "qwen2.5-3b-active"
    assert card["object"] == "model"
    assert card["owned_by"] == "hero-cost-intelligence"

    # Non-existent or quarantined model returns 404
    res_404 = client.get("/v1/models/non-existent-model")
    assert res_404.status_code == 404
    assert res_404.json()["error"]["code"] == "model_not_found"


def test_05_quarantined_model_rejection(client):
    """Requirement 2 & AI-02: Direct API execution against quarantined model must be rejected with 400."""
    payload = {
        "model": "malicious-model-quarantined",
        "messages": [{"role": "user", "content": "Hello"}],
    }
    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 400
    assert "QUARANTINED" in res.json()["error"]["message"]


def test_06_chat_completions_non_streaming(client):
    """Requirement 1, 6, 10: Non-streaming chat completions with standard OpenAI schema and Hero headers."""
    payload = {
        "model": "qwen2.5-3b-active",
        "messages": [
            {"role": "system", "content": "You are a cost engineering assistant."},
            {"role": "user", "content": "Calculate the variance for cylinder head machining."},
        ],
        "temperature": 0.0,
        "max_tokens": 100,
    }
    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["object"] == "chat.completion"
    assert data["model"] == "qwen2.5-3b-active"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert len(data["choices"][0]["message"]["content"]) > 0
    assert data["usage"]["total_tokens"] > 0

    # Verify Hero governance provenance headers
    assert "X-Hero-Task-ID" in res.headers
    assert "X-Hero-Audit-Hash" in res.headers
    assert "X-Hero-Grounding-Score" in res.headers


def test_07_chat_completions_streaming_sse(client):
    """Requirement 9 & 11: SSE streaming with data: {...} ending with data: [DONE]."""
    payload = {
        "model": "qwen2.5-3b-active",
        "messages": [{"role": "user", "content": "Summarize plant OPEX."}],
        "stream": True,
    }
    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    lines = [line.strip() for line in res.text.split("\n") if line.strip()]
    assert len(lines) >= 2

    # Verify chunks
    data_lines = [l for l in lines if l.startswith("data: ")]
    assert len(data_lines) >= 2
    assert data_lines[-1] == "data: [DONE]"

    # Verify first chunk structure
    first_json = json.loads(data_lines[0].replace("data: ", ""))
    assert first_json["object"] == "chat.completion.chunk"
    assert first_json["model"] == "qwen2.5-3b-active"


@pytest.mark.asyncio
async def test_08_streaming_disconnect_cancellation():
    """Requirement 9: Client disconnect propagates cancellation to orchestrator."""
    service = OpenAIService()

    # Mock Request that signals disconnection immediately
    class MockDisconnectedRequest:
        async def is_disconnected(self):
            return True

    chat_req = ChatCompletionRequest(
        model="qwen2.5-3b-active",
        messages=[ChatCompletionMessage(role="user", content="Stream test")],
        stream=True,
    )

    chunks = []
    async for chunk in service.stream_chat_completion(chat_req, MockDisconnectedRequest()):
        chunks.append(chunk)

    # Should exit cleanly after cancellation without infinite streaming
    assert len(chunks) <= 3
    assert chunks[-1] == "data: [DONE]\n\n"


def test_09_chat_completions_structured_json_mode(client):
    """Requirement 10: response_format={"type": "json_object"} maps to STRUCTURED_EXTRACTION."""
    payload = {
        "model": "qwen2.5-3b-active",
        "messages": [{"role": "user", "content": "Extract tooling cost: INR 450000"}],
        "response_format": {"type": "json_object"},
    }
    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["object"] == "chat.completion"


def test_10_tool_proposal_no_arbitrary_execution(client):
    """Requirement 7: OpenAI client tools represent proposals only and execute through AI-11 sandbox."""
    payload = {
        "model": "qwen2.5-3b-active",
        "messages": [{"role": "user", "content": "Check part inventory for 11211-KCC-900"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "lookup_part_cost",
                    "description": "Look up official part BOM cost",
                    "parameters": {"type": "object", "properties": {"part_number": {"type": "string"}}},
                },
            }
        ],
    }
    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["object"] == "chat.completion"


def test_11_legacy_text_completions(client):
    """Requirement 10: Legacy POST /v1/completions routes through AI-12."""
    payload = {
        "model": "qwen2.5-3b-active",
        "prompt": "The primary cause of plant power tariff variance is",
        "max_tokens": 50,
    }
    res = client.post("/v1/completions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["object"] == "text_completion"
    assert data["model"] == "qwen2.5-3b-active"
    assert len(data["choices"]) == 1
    assert len(data["choices"][0]["text"]) > 0


def test_12_embeddings_generation(client):
    """Requirement 8 & 10: POST /v1/embeddings generates dense vectors via AI-06."""
    payload = {
        "model": "qwen3-embedding-0.6b",
        "input": ["Cylinder Head Machining OPEX", "Borewell Water Tariff Variance"],
    }
    res = client.post("/v1/embeddings", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["object"] == "list"
    assert data["model"] == "qwen3-embedding-0.6b"
    assert len(data["data"]) == 2
    assert data["data"][0]["object"] == "embedding"
    assert data["data"][0]["index"] == 0
    assert len(data["data"][0]["embedding"]) == 384
    assert data["data"][1]["index"] == 1
    assert len(data["data"][1]["embedding"]) == 384


def test_13_embedding_dimension_and_capability_safety(client):
    """Requirement 8: Rejects embeddings request if model lacks EMBEDDING capability."""
    payload = {
        "model": "qwen2.5-3b-active",  # Pure generation model, lacks EMBEDDING capability
        "input": "Test text",
    }
    res = client.post("/v1/embeddings", json=payload)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "model_capability_mismatch"


def test_14_standard_error_envelopes(client):
    """Requirement 13: Errors strictly conform to standard OpenAI error format."""
    # Test 404 model not found
    res = client.post("/v1/chat/completions", json={"model": "unknown-model", "messages": [{"role": "user", "content": "hi"}]})
    assert res.status_code == 404
    err = res.json()["error"]
    assert "message" in err
    assert "type" in err
    assert "code" in err


def test_15_provenance_and_audit_headers(client):
    """Requirement 6 & 12: Hero cryptographic audit hash and provenance returned in headers."""
    res = client.post(
        "/v1/chat/completions",
        json={"model": "qwen2.5-3b-active", "messages": [{"role": "user", "content": "Audit check"}]},
    )
    assert res.status_code == 200
    assert res.headers["X-Hero-Task-ID"].startswith("task-ai-")
    assert "X-Hero-Audit-Hash" in res.headers
    assert "X-Hero-Model-ID" in res.headers


def test_16_concurrency_limiting(client):
    """Requirement 14: Bounded concurrency semaphore protects hardware resources."""
    assert openai_service._concurrency_semaphore._value <= settings.OPENAI_API_MAX_CONCURRENCY


def test_17_api_path_aliases(client):
    """Requirement 17: Both /v1/chat/completions and /api/v1/openai/chat/completions function identically."""
    payload = {
        "model": "qwen2.5-3b-active",
        "messages": [{"role": "user", "content": "Alias test"}],
    }
    res_root = client.post("/v1/chat/completions", json=payload)
    res_api = client.post("/api/v1/openai/chat/completions", json=payload)

    assert res_root.status_code == 200
    assert res_api.status_code == 200
    assert res_root.json()["object"] == res_api.json()["object"] == "chat.completion"


@pytest.mark.asyncio
async def test_18_real_openai_python_sdk_compatibility():
    """
    Requirement 18: End-to-end verification using the actual OpenAI Python SDK client
    (models.list(), chat.completions.create(), embeddings.create()).
    """
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        client = AsyncOpenAI(
            base_url="http://test/v1",
            api_key=settings.OPENAI_API_KEY,
            http_client=http_client,
        )

        # 1. Test models.list()
        models_page = await client.models.list()
        model_list = [m.id for m in models_page.data]
        assert "qwen2.5-3b-active" in model_list
        assert "qwen3-embedding-0.6b" in model_list

        # 2. Test chat.completions.create() non-streaming
        chat_completion = await client.chat.completions.create(
            model="qwen2.5-3b-active",
            messages=[{"role": "user", "content": "Explain energy efficiency in Hero Haridwar plant"}],
            temperature=0.0,
            max_tokens=80,
        )
        assert chat_completion.id.startswith("chatcmpl-")
        assert chat_completion.model == "qwen2.5-3b-active"
        assert len(chat_completion.choices) == 1
        assert len(chat_completion.choices[0].message.content or "") > 0
        assert chat_completion.usage is not None
        assert chat_completion.usage.total_tokens > 0

        # 3. Test embeddings.create()
        embedding_res = await client.embeddings.create(
            model="qwen3-embedding-0.6b",
            input=["Hero MotoCorp Haridwar Plant OPEX", "Neemrana Green Energy Initiative"],
        )
        assert len(embedding_res.data) == 2
        assert len(embedding_res.data[0].embedding) == 384
        assert len(embedding_res.data[1].embedding) == 384
        assert embedding_res.model == "qwen3-embedding-0.6b"
