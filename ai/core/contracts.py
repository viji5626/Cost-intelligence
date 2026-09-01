"""
Local AI Runtime Contracts, Interfaces, and Execution Protocols
Defines decoupled protocols for Generation, Embedding, Reranking, Vision/OCR, Lifecycle, and Tools.
"""

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, Dict, Generic, List, Optional, Protocol, TypeVar, runtime_checkable
from pydantic import BaseModel, Field

T = TypeVar("T")


class TaskType(str, Enum):
    REASONING = "REASONING"
    GROUNDED_REASONING = "GROUNDED_REASONING"
    STRUCTURED_EXTRACTION = "STRUCTURED_EXTRACTION"
    CLASSIFICATION = "CLASSIFICATION"
    SUMMARIZATION = "SUMMARIZATION"
    EMBEDDING = "EMBEDDING"
    RERANKING = "RERANKING"
    VISION_OCR = "VISION_OCR"
    TOOL_CALL = "TOOL_CALL"


class ModelFormatEnum(str, Enum):
    GGUF = "GGUF"
    ONNX = "ONNX"
    SAFE_TENSORS = "SAFE_TENSORS"


class ModelStatusEnum(str, Enum):
    QUARANTINED = "QUARANTINED"
    ACTIVE_REGISTERED = "ACTIVE_REGISTERED"
    REJECTED_QUARANTINED = "REJECTED_QUARANTINED"
    ARCHIVED = "ARCHIVED"


class ModelProvenance(BaseModel):
    """Cryptographic provenance attached to every model execution."""
    model_id: str
    model_version: str
    model_file_hash: str
    quantization: str
    runtime_engine: str
    runtime_profile: str
    context_length: int
    temperature: float
    seed: int
    embedding_model_id: Optional[str] = None
    reranker_model_id: Optional[str] = None
    prompt_template_version: str = "v1.0"
    execution_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ModelManifestData(BaseModel):
    """Offline metadata manifest for any registered model."""
    model_id: str
    model_version: str = "1.0.0"
    display_name: str
    file_path: str
    file_size_bytes: int
    sha256_checksum: str
    format: ModelFormatEnum = ModelFormatEnum.GGUF
    quantization: str = "Q4_K_M"
    architecture: str = "qwen2"
    parameter_count: str = "3.0B"
    supported_tasks: List[TaskType] = Field(default_factory=lambda: [TaskType.REASONING])
    embedding_dimension: Optional[int] = None
    distance_metric: Optional[str] = "COSINE"
    base_context_length: int = 32768
    recommended_context_length: int = 4096
    estimated_weights_vram_mb: int = 2100
    estimated_kv_cache_mb_per_4k: int = 450
    status: ModelStatusEnum = ModelStatusEnum.QUARANTINED
    provenance_author: str = "Hero Engineering"
    imported_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    quarantine_notes: Optional[str] = None


class AIExecutionEnvelope(BaseModel, Generic[T]):
    """
    Standard AI Execution Envelope wrapping all AI outputs delivered to business modules.
    Guarantees audit traceability, evidence grounding attribution, and provenance verification.
    """
    task_id: str
    task_type: TaskType
    status: str = "SUCCESS"  # SUCCESS, DEGRADED, INSUFFICIENT_EVIDENCE, ERROR
    result: T
    raw_content: str
    grounding_score: Optional[float] = None
    evidence_citations: List[Dict[str, Any]] = Field(default_factory=list)
    usage: Dict[str, int] = Field(default_factory=dict)
    latency_seconds: float = 0.0
    provenance: ModelProvenance
    audit_hash: str = ""

    def compute_audit_hash(self) -> str:
        """Computes SHA-256 digest of core payload and provenance for immutable audit."""
        payload = {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "status": self.status,
            "raw_content": self.raw_content,
            "provenance": self.provenance.model_dump(),
        }
        encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def model_post_init(self, __context: Any) -> None:
        if not self.audit_hash:
            self.audit_hash = self.compute_audit_hash()


# --- Decoupled Task Provider Contracts ---

@runtime_checkable
class InferenceEngineContract(Protocol):
    """Protocol for generative SLM inference engines (GGUF / Llama.cpp)."""

    async def load_model(
        self,
        model_id: str,
        context_length: Optional[int] = None,
        gpu_layers_override: Optional[int] = None,
        force_cpu: bool = False,
        timeout_seconds: float = 60.0,
        **kwargs: Any,
    ) -> bool:
        ...

    async def unload_model(self) -> bool:
        ...

    async def is_ready(self) -> bool:
        ...

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
        stop: Optional[List[str]] = None,
        timeout_seconds: float = 60.0,
    ) -> str:
        ...

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1024,
        temperature: float = 0.0,
        stop: Optional[List[str]] = None,
        timeout_seconds: float = 60.0,
    ) -> AsyncIterator[str]:
        ...

    def cancel_current_generation(self) -> None:
        ...

    def get_device_info(self) -> Dict[str, Any]:
        ...


@runtime_checkable
class EmbeddingEngineContract(Protocol):
    """Protocol for dense vector embedding generation."""

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        ...

    def get_dimension(self) -> int:
        """Returns the dynamic vector dimension of the active model."""
        ...

    def is_normalized(self) -> bool:
        ...


@runtime_checkable
class RerankerEngineContract(Protocol):
    """Protocol for cross-encoder re-ranking engines."""

    async def rerank_async(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        ...

    def get_model_name(self) -> str:
        ...


@runtime_checkable
class VisionOCREngineContract(Protocol):
    """Protocol for OCR / Vision models extracting handwritten text & drawings."""

    async def extract_text(self, document_bytes: bytes, mime_type: Optional[str] = None, model_id: Optional[str] = None) -> str:
        ...

    async def extract_structured(self, document_bytes: bytes, json_schema: Dict[str, Any], model_id: Optional[str] = None) -> Dict[str, Any]:
        ...


@runtime_checkable
class LifecycleManagerContract(Protocol):
    """Protocol for hardware-aware model lifecycle and memory purging."""

    async def acquire_model(self, task_type: TaskType, model_id: str) -> Any:
        ...

    async def release_current_model(self) -> None:
        ...

    def get_status(self) -> Dict[str, Any]:
        ...


@runtime_checkable
class ToolRegistryContract(Protocol):
    """Protocol for sandboxed domain tools and local MCP management."""

    def register_tool(self, name: str, description: str, parameters_schema: Dict[str, Any], handler: Any) -> None:
        ...

    async def execute_tool(self, name: str, arguments: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
        ...
