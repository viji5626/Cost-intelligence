"""
Phase AI-12 Test Suite: Central AI Orchestrator & Task Router
Tests task-specific execution plans, dynamic routing, model override validation,
hardware admission, grounded reasoning, structured extraction, pure embedding/reranking,
tool loop execution, idempotency, streaming cancellation, and real native GGUF integration.
"""

import asyncio
import hashlib
import json
import pytest
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

from ai.core.contracts import (
    AIExecutionEnvelope,
    ModelFormatEnum,
    ModelManifestData,
    ModelStatusEnum,
    TaskType,
)
from ai.grammar.schemas import IdeaDecompositionOutputSchema, ToolCallOutputSchema
from ai.hardware.fit_engine import FitStatusEnum, HardwareFitResult, OffloadStrategyEnum, RecommendationEnum
from ai.hardware.fit_service import HardwareFitService
from ai.hardware.profiles import RuntimeProfileName
from ai.orchestrator.central_orchestrator import AIOrchestrator
from ai.orchestrator.models import (
    ExecutionPlan,
    PipelineStageEnum,
    TaskRequest,
    TaskRoutingDecision,
)
from ai.orchestrator.task_router import TaskRouter
from ai.providers.native_gguf import NativeGGUFEngine
from ai.registry.manifest_registry import ManifestRegistry


# ==============================================================================
# FIXTURES & TEST SETUP
# ==============================================================================

@pytest.fixture
def mock_registry():
    """Provides a pre-populated manifest registry with reasoning, embedding, and reranker models."""
    from ai.registry.models import ModelCapabilityEnum, ModelFormatEnum, ModelManifest, ModelStatusEnum, ModelTaskTypeEnum
    from ai.registry.registry_service import model_registry_service

    reg = ManifestRegistry()

    # Active Reasoning Model
    m_reason = ModelManifest(
        model_id="qwen2.5-3b-active",
        version="1.0.0",
        display_name="Qwen 2.5 3B Active",
        file_path="models/gguf/qwen2.5-3b-instruct-q4_k_m.gguf",
        file_size_bytes=2000000000,
        sha256_checksum="687635678abcdef0123456789abcdef0123456789abcdef0123456789abcdef0",
        format=ModelFormatEnum.GGUF,
        primary_task_type=ModelTaskTypeEnum.GENERATION,
        capabilities=[ModelCapabilityEnum.GENERATION],
        status=ModelStatusEnum.ACTIVE_REGISTERED,
    )
    model_registry_service.register_manifest(m_reason, overwrite=True)
    reg.register_manifest(ModelManifestData(
        model_id=m_reason.model_id,
        model_version=m_reason.version,
        display_name=m_reason.display_name,
        file_path=m_reason.file_path,
        file_size_bytes=m_reason.file_size_bytes,
        sha256_checksum=m_reason.sha256_checksum,
        format=m_reason.format,
        supported_tasks=[TaskType.REASONING, TaskType.STRUCTURED_EXTRACTION, TaskType.TOOL_CALL],
        status=m_reason.status,
    ))

    # Quarantined Model
    m_quar = ModelManifest(
        model_id="quarantined-model-v1",
        version="1.0.0",
        display_name="Quarantined Model",
        file_path="models/gguf/quarantined.gguf",
        file_size_bytes=2000000000,
        sha256_checksum="1111222233334444555566667777888899990000aaaabbbbccccddddeeeeffff",
        format=ModelFormatEnum.GGUF,
        primary_task_type=ModelTaskTypeEnum.GENERATION,
        capabilities=[ModelCapabilityEnum.GENERATION],
        status=ModelStatusEnum.QUARANTINED,
    )
    model_registry_service.register_manifest(m_quar, overwrite=True)
    reg.register_manifest(ModelManifestData(
        model_id=m_quar.model_id,
        model_version=m_quar.version,
        display_name=m_quar.display_name,
        file_path=m_quar.file_path,
        file_size_bytes=m_quar.file_size_bytes,
        sha256_checksum=m_quar.sha256_checksum,
        format=m_quar.format,
        supported_tasks=[TaskType.REASONING],
        status=m_quar.status,
    ))

    # Embedding Model
    m_emb = ModelManifest(
        model_id="bge-large-embed-active",
        version="1.0.0",
        display_name="BGE Large En Active",
        file_path="models/gguf/bge-large-en-v1.5-q4_k_m.gguf",
        file_size_bytes=600000000,
        sha256_checksum="2222333344445555666677778888999900001111aaaabbbbccccddddeeeeffff",
        format=ModelFormatEnum.GGUF,
        primary_task_type=ModelTaskTypeEnum.EMBEDDING,
        capabilities=[ModelCapabilityEnum.EMBEDDING],
        embedding_dimension=384,
        status=ModelStatusEnum.ACTIVE_REGISTERED,
    )
    model_registry_service.register_manifest(m_emb, overwrite=True)
    reg.register_manifest(ModelManifestData(
        model_id=m_emb.model_id,
        model_version=m_emb.version,
        display_name=m_emb.display_name,
        file_path=m_emb.file_path,
        file_size_bytes=m_emb.file_size_bytes,
        sha256_checksum=m_emb.sha256_checksum,
        format=m_emb.format,
        supported_tasks=[TaskType.EMBEDDING],
        status=m_emb.status,
    ))

    # Reranker Model
    m_rerank = ModelManifest(
        model_id="bge-reranker-active",
        version="1.0.0",
        display_name="BGE Reranker Active",
        file_path="models/gguf/bge-reranker-large-q4_k_m.gguf",
        file_size_bytes=600000000,
        sha256_checksum="3333444455556666777788889999000011112222aaaabbbbccccddddeeeeffff",
        format=ModelFormatEnum.GGUF,
        primary_task_type=ModelTaskTypeEnum.RERANKER,
        capabilities=[ModelCapabilityEnum.RERANKING],
        status=ModelStatusEnum.ACTIVE_REGISTERED,
    )
    model_registry_service.register_manifest(m_rerank, overwrite=True)
    reg.register_manifest(ModelManifestData(
        model_id=m_rerank.model_id,
        model_version=m_rerank.version,
        display_name=m_rerank.display_name,
        file_path=m_rerank.file_path,
        file_size_bytes=m_rerank.file_size_bytes,
        sha256_checksum=m_rerank.sha256_checksum,
        format=m_rerank.format,
        supported_tasks=[TaskType.RERANKING],
        status=m_rerank.status,
    ))

    return reg


# ==============================================================================
# 1. TASK ROUTER & EXECUTION PLAN TESTS
# ==============================================================================

def test_01_task_router_resolves_task_to_model_and_plan(mock_registry):
    """Test: TaskRouter maps tasks to appropriate models and produces stage-specific plans."""
    router = TaskRouter(registry=mock_registry)

    # 1. Reasoning Task
    req_reason = TaskRequest(task_type=TaskType.REASONING, prompt="Analyze weight reduction.")
    dec_reason = router.resolve_routing(req_reason)
    assert dec_reason.is_routed is True
    assert dec_reason.selected_model.model_id == "qwen2.5-3b-active"
    plan_reason = router.create_execution_plan(req_reason, dec_reason)
    assert PipelineStageEnum.GENERATION in plan_reason.required_stages
    assert PipelineStageEnum.EMBEDDING not in plan_reason.required_stages

    # 2. Embedding Task
    req_embed = TaskRequest(task_type=TaskType.EMBEDDING, input_texts=["ECN part change"])
    dec_embed = router.resolve_routing(req_embed)
    assert dec_embed.is_routed is True
    assert dec_embed.selected_model.model_id == "bge-large-embed-active"
    plan_embed = router.create_execution_plan(req_embed, dec_embed)
    assert plan_embed.required_stages == [PipelineStageEnum.ROUTING, PipelineStageEnum.EMBEDDING]

    # 3. Reranking Task
    req_rerank = TaskRequest(task_type=TaskType.RERANKING, prompt="query", rerank_candidates=[{"text": "c1"}])
    dec_rerank = router.resolve_routing(req_rerank)
    assert dec_rerank.is_routed is True
    assert dec_rerank.selected_model.model_id == "bge-reranker-active"
    plan_rerank = router.create_execution_plan(req_rerank, dec_rerank)
    assert plan_rerank.required_stages == [PipelineStageEnum.ROUTING, PipelineStageEnum.RERANKER_ONLY]


def test_02_model_override_validation_and_rejection(mock_registry):
    """Test: Model overrides validate registration, status, and task support; rejects invalid overrides."""
    router = TaskRouter(registry=mock_registry)

    # Valid override
    req_valid = TaskRequest(
        task_type=TaskType.REASONING,
        prompt="Test",
        model_id_override="qwen2.5-3b-active",
    )
    dec_valid = router.resolve_routing(req_valid)
    assert dec_valid.is_routed is True
    assert dec_valid.selected_model.model_id == "qwen2.5-3b-active"

    # Nonexistent override
    req_none = TaskRequest(
        task_type=TaskType.REASONING,
        prompt="Test",
        model_id_override="nonexistent-model-xyz",
    )
    dec_none = router.resolve_routing(req_none)
    assert dec_none.is_routed is False
    assert "does not exist" in dec_none.explanation

    # Quarantined override rejected
    req_quar = TaskRequest(
        task_type=TaskType.REASONING,
        prompt="Test",
        model_id_override="quarantined-model-v1",
    )
    dec_quar = router.resolve_routing(req_quar)
    assert dec_quar.is_routed is False
    assert "quarantined or inactive" in dec_quar.explanation

    # Task unsupported override rejected (trying to run reasoning on embedding model)
    req_unsupp = TaskRequest(
        task_type=TaskType.REASONING,
        prompt="Test",
        model_id_override="bge-large-embed-active",
    )
    dec_unsupp = router.resolve_routing(req_unsupp)
    assert dec_unsupp.is_routed is False
    assert "does not support task type" in dec_unsupp.explanation


def test_03_hardware_admission_gating_in_router(mock_registry):
    """Test: UNSAFE hardware verdict halts model selection and explains reason."""
    mock_service = MagicMock()
    mock_service.evaluate_model_fit.return_value = HardwareFitResult(
        compatible=False,
        status=FitStatusEnum.UNSAFE,
        recommendation=RecommendationEnum.NOT_RECOMMENDED,
        estimated_model_weights_mb=4000,
        estimated_kv_cache_mb=1000,
        estimated_runtime_overhead_mb=500,
        estimated_peak_memory_mb=5500,
        recommended_offload_strategy=OffloadStrategyEnum.CPU_ONLY,
        recommended_gpu_layers=0,
        total_model_layers=33,
        recommended_context_length=4096,
        recommended_runtime_profile=RuntimeProfileName.PROFILE_BALANCED,
        safety_headroom_mb=-1000,
        reasons=["VRAM budget exceeded"],
    )
    router = TaskRouter(registry=mock_registry, fit_service=mock_service)

    req = TaskRequest(task_type=TaskType.REASONING, prompt="Test")
    dec = router.resolve_routing(req)
    assert dec.is_routed is False
    assert "Hardware UNSAFE" in dec.rejection_reasons.get("qwen2.5-3b-active", "")


# ==============================================================================
# 2. CENTRAL ORCHESTRATOR EXECUTION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_04_end_to_end_reasoning_task_execution(mock_registry):
    """Test: Orchestrator executes standard reasoning task returning AIExecutionEnvelope."""
    router = TaskRouter(registry=mock_registry)
    orchestrator = AIOrchestrator(router=router)

    req = TaskRequest(
        task_id="task-reason-01",
        task_type=TaskType.REASONING,
        prompt="Analyze aluminum handlebar material substitution feasibility.",
    )
    envelope = await orchestrator.execute_task(req)

    assert envelope.status == "SUCCESS"
    assert envelope.task_type == TaskType.REASONING
    assert isinstance(envelope.result, str)
    assert envelope.provenance.model_id == "qwen2.5-3b-active"
    assert len(envelope.audit_hash) == 64


@pytest.mark.asyncio
async def test_05_end_to_end_grounded_reasoning_execution(mock_registry):
    """Test: Grounded reasoning evaluates evidence, attaches citations, and computes grounding score."""
    router = TaskRouter(registry=mock_registry)
    orchestrator = AIOrchestrator(router=router)

    chunks = [
        {
            "chunk_id": "ECN-2024-001-C1",
            "doc_id": "ECN-2024-001",
            "content": "ECN-2024-001 implemented Aluminum Handlebar 53100-KTR-900 on Splendor Plus achieving 450g reduction.",
            "source_type": "ECN",
            "part_number": "53100-KTR-900",
            "model_code": "SPLENDOR_PLUS",
            "effective_date": "2024-02-15",
            "status": "RELEASED",
            "authority_weight": 1.0,
        }
    ]

    req = TaskRequest(
        task_id="task-grounded-01",
        task_type=TaskType.GROUNDED_REASONING,
        prompt="Verify handlebar weight reduction feasibility.",
        retrieved_chunks=chunks,
        grounding_required=True,
    )
    envelope = await orchestrator.execute_task(req)

    assert envelope.status == "SUCCESS"
    assert envelope.grounding_score is not None
    assert envelope.grounding_score > 0.0
    assert len(envelope.evidence_citations) >= 1
    assert envelope.evidence_citations[0]["doc_id"] == "ECN-2024-001"


@pytest.mark.asyncio
async def test_06_grounded_reasoning_insufficient_evidence_status(mock_registry):
    """Test: When grounding is required and evidence is missing, returns INSUFFICIENT_EVIDENCE."""
    router = TaskRouter(registry=mock_registry)
    orchestrator = AIOrchestrator(router=router)

    req = TaskRequest(
        task_id="task-grounded-fail",
        task_type=TaskType.GROUNDED_REASONING,
        prompt="Verify impossible premise with zero retrieved records.",
        retrieved_chunks=[],
        grounding_required=True,
    )
    envelope = await orchestrator.execute_task(req)

    assert envelope.status == "INSUFFICIENT_EVIDENCE"
    assert "Evidence grounding failed" in envelope.result


@pytest.mark.asyncio
async def test_07_end_to_end_structured_extraction_execution(mock_registry):
    """Test: Structured extraction returns typed Pydantic object within envelope."""
    router = TaskRouter(registry=mock_registry)
    orchestrator = AIOrchestrator(router=router)

    req = TaskRequest(
        task_id="task-struct-01",
        task_type=TaskType.STRUCTURED_EXTRACTION,
        prompt="Idea: Replace steel handlebar 53100-KTR-900 with aluminum alloy on Splendor Plus.",
        schema_model=IdeaDecompositionOutputSchema,
    )
    envelope = await orchestrator.execute_task(req)

    assert envelope.status == "SUCCESS"
    assert isinstance(envelope.result, IdeaDecompositionOutputSchema)
    assert envelope.result.target_component.lower() == "handlebar"
    assert envelope.result.target_part_number == "53100-KTR-900"


@pytest.mark.asyncio
async def test_08_end_to_end_embedding_task_execution(mock_registry):
    """Test: Pure embedding task executes without invoking generative SLM."""
    router = TaskRouter(registry=mock_registry)
    orchestrator = AIOrchestrator(router=router)

    req = TaskRequest(
        task_id="task-embed-01",
        task_type=TaskType.EMBEDDING,
        input_texts=["Handlebar material substitution", "Brake lever optimization"],
    )
    envelope = await orchestrator.execute_task(req)

    assert envelope.status == "SUCCESS"
    assert envelope.task_type == TaskType.EMBEDDING
    assert len(envelope.result) == 2
    assert len(envelope.result[0]) == 384  # 384d vector default


@pytest.mark.asyncio
async def test_09_end_to_end_reranking_task_execution(mock_registry):
    """Test: Pure reranking task executes cross-encoder scoring without generative SLM."""
    router = TaskRouter(registry=mock_registry)
    orchestrator = AIOrchestrator(router=router)

    candidates = [
        {"id": "D1", "text": "Aluminum handlebar coring and thickness optimization."},
        {"id": "D2", "text": "Plant electricity consumption summary."},
    ]
    req = TaskRequest(
        task_id="task-rerank-01",
        task_type=TaskType.RERANKING,
        prompt="Handlebar optimization",
        rerank_candidates=candidates,
    )
    envelope = await orchestrator.execute_task(req)

    assert envelope.status == "SUCCESS"
    assert envelope.task_type == TaskType.RERANKING
    assert len(envelope.result) == 2
    assert envelope.result[0]["id"] == "D1"


@pytest.mark.asyncio
async def test_10_tool_pipeline_loop_orchestration(mock_registry):
    """Test: Tool execution loop proposes tool, validates with AI-11, and feeds result back to generation."""
    router = TaskRouter(registry=mock_registry)
    orchestrator = AIOrchestrator(router=router)

    req = TaskRequest(
        task_id="task-tool-01",
        task_type=TaskType.TOOL_CALL,
        prompt="Calculate financial opportunity for reducing handlebar cost from 485.5 to 450 INR with 600,000 volume.",
        allow_tool_calls=True,
    )
    envelope = await orchestrator.execute_task(req)

    assert envelope.status == "SUCCESS"
    assert envelope.task_type == TaskType.TOOL_CALL
    assert "tool_executions" in envelope.result
    assert len(envelope.result["tool_executions"]) >= 1


@pytest.mark.asyncio
async def test_11_idempotency_duplicate_request_protection(mock_registry):
    """Test: Repeating identical task request returns cached envelope immediately."""
    router = TaskRouter(registry=mock_registry)
    orchestrator = AIOrchestrator(router=router)

    req = TaskRequest(
        task_id="task-idempotent-01",
        task_type=TaskType.REASONING,
        prompt="Idempotency test query prompt.",
    )
    env1 = await orchestrator.execute_task(req)
    env2 = await orchestrator.execute_task(req)

    assert env1.audit_hash == env2.audit_hash
    assert env1.task_id == env2.task_id


@pytest.mark.asyncio
async def test_12_streaming_chat_token_delivery(mock_registry):
    """Test: stream_task yields token chunks asynchronously in real-time."""
    router = TaskRouter(registry=mock_registry)
    orchestrator = AIOrchestrator(router=router)

    req = TaskRequest(
        task_id="task-stream-01",
        task_type=TaskType.REASONING,
        prompt="Stream test tokens.",
    )
    tokens: List[str] = []
    async for token in orchestrator.stream_task(req):
        tokens.append(token)

    assert len(tokens) >= 1
    assert any("mock" in t.lower() or len(t) > 0 for t in tokens)


def test_13_cancellation_propagation(mock_registry):
    """Test: cancel_task propagates directly to inference engine."""
    mock_inference = MagicMock(spec=NativeGGUFEngine)
    router = TaskRouter(registry=mock_registry)
    orchestrator = AIOrchestrator(router=router, inference_engine=mock_inference)

    orchestrator.cancel_task()
    mock_inference.cancel_current_generation.assert_called_once()


# ==============================================================================
# 3. REAL NATIVE GGUF INTEGRATION TEST
# ==============================================================================

@pytest.mark.asyncio
async def test_14_real_native_gguf_orchestration_integration(mock_registry):
    """
    Test: Real native GGUF inference engine integration via AIOrchestrator.
    Verifies full lifecycle loading, generation, context assembly, and envelope wrapping.
    """
    from ai.registry.models import ModelCapabilityEnum, ModelFormatEnum, ModelManifest, ModelStatusEnum, ModelTaskTypeEnum
    from ai.registry.registry_service import model_registry_service

    manifest = ModelManifest(
        model_id="qwen2.5-3b-active",
        model_version="1.0.0",
        display_name="Qwen 2.5 3B Active",
        file_path="models/gguf/qwen2.5-3b-instruct-q4_k_m.gguf",
        file_size_bytes=2000000000,
        sha256_checksum="687635678abcdef0123456789abcdef0123456789abcdef0123456789abcdef0",
        format=ModelFormatEnum.GGUF,
        primary_task_type=ModelTaskTypeEnum.GENERATION,
        capabilities=[ModelCapabilityEnum.GENERATION],
        status=ModelStatusEnum.ACTIVE_REGISTERED,
    )
    model_registry_service.register_manifest(manifest, overwrite=True)

    native_engine = NativeGGUFEngine()
    router = TaskRouter(registry=mock_registry)
    orchestrator = AIOrchestrator(router=router, inference_engine=native_engine)

    req = TaskRequest(
        task_id="task-native-integration-01",
        task_type=TaskType.REASONING,
        prompt="Provide engineering summary for Hero Splendor handlebar cost reduction.",
        model_id_override="qwen2.5-3b-active",
    )
    envelope = await orchestrator.execute_task(req)

    assert envelope.status == "SUCCESS"
    assert envelope.provenance.model_id == "qwen2.5-3b-active"
    assert envelope.provenance.runtime_engine == "llama.cpp"
    assert len(envelope.audit_hash) == 64
    assert len(envelope.raw_content) > 0
