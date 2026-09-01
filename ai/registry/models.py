"""
Model Registry Schemas, Manifest Specifications & Enums
Canonical specifications for local offline model manifests, capabilities, and lifecycle states.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class ModelTaskTypeEnum(str, Enum):
    GENERATION = "GENERATION"
    EMBEDDING = "EMBEDDING"
    RERANKER = "RERANKER"
    VISION_OCR = "VISION_OCR"
    OTHER = "OTHER"


class ModelCapabilityEnum(str, Enum):
    GENERATION = "GENERATION"
    EMBEDDING = "EMBEDDING"
    RERANKING = "RERANKING"
    VISION = "VISION"
    STRUCTURED_OUTPUT = "STRUCTURED_OUTPUT"
    GRAMMAR = "GRAMMAR"
    STREAMING = "STREAMING"


class ModelFormatEnum(str, Enum):
    GGUF = "GGUF"
    ONNX = "ONNX"
    SAFE_TENSORS = "SAFE_TENSORS"


class ModelStatusEnum(str, Enum):
    IMPORTED = "IMPORTED"
    QUARANTINED = "QUARANTINED"
    VALIDATING = "VALIDATING"
    ACTIVE_REGISTERED = "ACTIVE_REGISTERED"
    REJECTED_INVALID = "REJECTED_INVALID"
    REJECTED_INCOMPATIBLE = "REJECTED_INCOMPATIBLE"
    ARCHIVED = "ARCHIVED"


class ModelManifest(BaseModel):
    """Canonical offline Model Manifest specification."""

    # 1. Identity & Provenance
    model_id: str = Field(..., description="Unique immutable model identifier (e.g. qwen2.5-3b-instruct-q4_k_m)")
    display_name: str = Field(..., description="Human-readable model name")
    version: str = Field(default="1.0.0", description="Semantic model/weights version")
    provider: str = Field(default="BUILTIN_GGUF", description="Target execution provider")
    manifest_version: str = Field(default="1.0", description="Manifest schema specification version")
    provenance_author: str = Field(default="Hero Cost Intelligence Platform", description="Origin / author attribution")
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    # 2. Binary File & Integrity
    file_path: str = Field(..., description="Normalized absolute or relative path to local model binary")
    file_size_bytes: int = Field(..., ge=0, description="Binary file size in bytes")
    checksum_algorithm: str = Field(default="SHA-256", description="Cryptographic hash algorithm")
    sha256_checksum: str = Field(..., min_length=64, max_length=64, description="Cryptographic SHA-256 digest")
    format: ModelFormatEnum = Field(default=ModelFormatEnum.GGUF, description="Binary model format")
    quantization: str = Field(default="Q4_K_M", description="Quantization scheme (e.g. Q4_K_M, Q8_0, FP16)")

    # 3. Architecture & Parameter Characteristics
    architecture: str = Field(default="qwen2", description="Base model tensor architecture (e.g. qwen2, llama, bert)")
    parameter_count: str = Field(default="3.0B", description="Reported parameter count (e.g. 3.09B, 0.6B)")
    context_length: int = Field(default=4096, ge=128, description="Maximum supported context window in tokens")
    recommended_context_length: int = Field(default=4096, ge=128, description="Recommended context window for baseline")

    # 4. Task Types & Explicit Capabilities
    primary_task_type: ModelTaskTypeEnum = Field(default=ModelTaskTypeEnum.GENERATION)
    capabilities: List[ModelCapabilityEnum] = Field(default_factory=lambda: [ModelCapabilityEnum.GENERATION])

    # 5. Embedding Model Specific Metadata (Dynamic Dimensions)
    embedding_dimension: Optional[int] = Field(default=None, description="Dynamic embedding vector dimensionality")
    distance_metric: Optional[str] = Field(default="COSINE", description="Target vector similarity metric")
    normalization_behavior: Optional[str] = Field(default="L2_UNIT", description="Vector normalization rule")
    pooling_behavior: Optional[str] = Field(default="MEAN", description="Embedding pooling method (MEAN, CLS)")

    # 6. Generation & Grammar Features
    chat_template: Optional[str] = Field(default="chatml", description="Chat template format (e.g. chatml, llama3)")
    tokenizer_identity: Optional[str] = Field(default="qwen2", description="Tokenizer identifier")
    supports_gbnf_grammar: bool = Field(default=True, description="Supports GBNF logit masking")
    supports_streaming: bool = Field(default=True, description="Supports async token streaming")
    supports_vision: bool = Field(default=False, description="Supports multi-modal image input")

    # 7. Hardware Estimation & Runtime Backends
    supported_backends: List[str] = Field(default_factory=lambda: ["BUILTIN_GGUF", "CPU_SIMD"])
    estimated_ram_mb: int = Field(default=2400, ge=0, description="Estimated host RAM allocation in MB")
    estimated_vram_mb: int = Field(default=2200, ge=0, description="Estimated dedicated VRAM allocation in MB")

    # 8. Lifecycle & Quarantine State
    status: ModelStatusEnum = Field(default=ModelStatusEnum.QUARANTINED, description="Active onboarding/readiness status")
    is_default: bool = Field(default=False, description="Whether this model is default for its primary task type")
    validation_errors: List[str] = Field(default_factory=list, description="Validation issues caught during quarantine")
    quarantine_notes: Optional[str] = Field(default=None, description="Audit notes explaining quarantine reason")

    @field_validator("embedding_dimension")
    @classmethod
    def validate_embedding_dimension(cls, v: Optional[int], info) -> Optional[int]:
        data = info.data
        caps = data.get("capabilities", [])
        primary_task = data.get("primary_task_type")
        if primary_task == ModelTaskTypeEnum.EMBEDDING or ModelCapabilityEnum.EMBEDDING in caps:
            if v is None or v <= 0:
                raise ValueError("embedding_dimension must be a positive integer for EMBEDDING models.")
        return v


class ModelRegistrationRequest(BaseModel):
    """Request payload for onboarding a new local model into quarantine."""
    model_id: str
    display_name: str
    file_path: str
    primary_task_type: ModelTaskTypeEnum = ModelTaskTypeEnum.GENERATION
    capabilities: List[ModelCapabilityEnum] = Field(default_factory=lambda: [ModelCapabilityEnum.GENERATION])
    architecture: str = "qwen2"
    quantization: str = "Q4_K_M"
    parameter_count: str = "3.0B"
    context_length: int = 4096
    embedding_dimension: Optional[int] = None
    distance_metric: Optional[str] = "COSINE"
    supports_gbnf_grammar: bool = True
    supports_streaming: bool = True
    supports_vision: bool = False
    estimated_ram_mb: Optional[int] = None
    estimated_vram_mb: Optional[int] = None
    set_as_default: bool = False
    notes: Optional[str] = None
