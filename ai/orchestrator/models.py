"""
AI Orchestration & Routing Models (AI-12)
Defines execution plans, stage traces, routing decisions, and task request envelopes.
"""

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel, Field

from ai.core.contracts import ModelManifestData, TaskType


class PipelineStageEnum(str, Enum):
    """Discrete pipeline stages executed by the orchestrator."""
    ROUTING = "ROUTING"
    ACQUIRE_MODEL = "ACQUIRE_MODEL"
    RETRIEVAL = "RETRIEVAL"
    RERANKING = "RERANKING"
    EVIDENCE_EVALUATION = "EVIDENCE_EVALUATION"
    CONTEXT_BUILD = "CONTEXT_BUILD"
    GENERATION = "GENERATION"
    STRUCTURED_VALIDATION = "STRUCTURED_VALIDATION"
    TOOL_PIPELINE = "TOOL_PIPELINE"
    EMBEDDING = "EMBEDDING"
    RERANKER_ONLY = "RERANKER_ONLY"
    OCR_ONLY = "OCR_ONLY"


class ExecutionStageTrace(BaseModel):
    """Detailed audit trace for an individual pipeline execution stage."""
    stage_name: PipelineStageEnum
    status: str = "SUCCESS"  # SUCCESS, SKIPPED, FAILED
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    latency_seconds: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class ExecutionPlan(BaseModel):
    """
    Task-specific execution plan defining exact stages and resource bounds.
    Eliminates monolithic one-size-fits-all pipeline execution.
    """
    task_id: str
    request_id: str
    task_type: TaskType
    provider: str
    model_id: str
    model_version: str
    model_file_path: str
    runtime_profile: str
    required_stages: List[PipelineStageEnum]
    grounding_required: bool = False
    context_policy: Dict[str, Any] = Field(default_factory=dict)
    context_limit: Optional[int] = None
    tool_policy: Dict[str, Any] = Field(default_factory=dict)
    temperature: float = 0.0
    seed: int = 42
    max_tokens: int = 512
    timeout_seconds: float = 60.0


class TaskRequest(BaseModel):
    """Standard input request envelope for the central AI Orchestrator."""
    task_id: str = Field(default_factory=lambda: f"task-ai-{int(datetime.now(timezone.utc).timestamp()*1000)}")
    request_id: str = Field(default_factory=lambda: f"req-ai-{int(datetime.now(timezone.utc).timestamp()*1000)}")
    task_type: TaskType = TaskType.REASONING
    system_prompt: Optional[str] = None
    prompt: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None
    schema_model: Optional[Any] = Field(default=None, description="Pydantic model class or schema dict")
    model_id_override: Optional[str] = None
    retrieved_chunks: Optional[List[Dict[str, Any]]] = None
    input_texts: Optional[List[str]] = None  # For EMBEDDING
    rerank_candidates: Optional[List[Dict[str, Any]]] = None  # For RERANKING
    document_bytes: Optional[bytes] = None  # For VISION_OCR
    mime_type: Optional[str] = None  # For VISION_OCR
    json_schema: Optional[Dict[str, Any]] = None
    grounding_required: bool = False
    context_limit: Optional[int] = None
    temperature: float = 0.0
    seed: int = 42
    max_tokens: int = 512
    timeout_seconds: float = 60.0
    dry_run: bool = False
    allow_tool_calls: bool = False
    provider_override: Optional[str] = None  # AUTO, BUILTIN_NATIVE_GGUF, OLLAMA, LM_STUDIO, OPENAI_COMPATIBLE
    fallback_policy: str = "FALLBACK_DISABLED"  # FALLBACK_DISABLED, FALLBACK_BUILTIN_LOCAL, FALLBACK_ALLOWED_LIST
    caller_identity: str = "orchestrator-client"

    def compute_request_signature(self) -> str:
        """Computes deterministic hash for idempotency checking."""
        content = self.prompt or str(self.messages) or str(self.input_texts) or str(self.rerank_candidates)
        payload = {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "content": content,
            "provider_override": self.provider_override,
            "temperature": self.temperature,
            "seed": self.seed,
            "grounding_required": self.grounding_required,
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


class TaskRoutingDecision(BaseModel):
    """Outcome of TaskRouter policy and capability resolution."""
    task_id: str
    task_type: TaskType
    selected_model: Optional[ModelManifestData] = None
    provider_type: str = "BUILTIN_NATIVE_GGUF"
    requested_provider: Optional[str] = None
    actual_provider: Optional[str] = None
    fallback_occurred: bool = False
    fallback_reason: Optional[str] = None
    runtime_profile: str = "AUTO"
    hardware_verdict: str = "SAFE"
    explanation: str
    rejection_reasons: Dict[str, str] = Field(default_factory=dict)
    is_routed: bool = True
