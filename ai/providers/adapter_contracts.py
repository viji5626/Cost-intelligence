"""
Provider Adapter Layer Contracts & Telemetry Models
Defines protocols, health models, telemetry structures, and fallback policies for local AI providers.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional
from pydantic import BaseModel, Field

from ai.core.contracts import TaskType
from ai.providers.exceptions import AIProviderError


class ProviderTypeEnum(str, Enum):
    BUILTIN_NATIVE_GGUF = "BUILTIN_NATIVE_GGUF"
    BUILTIN_NATIVE_EMBEDDING = "BUILTIN_NATIVE_EMBEDDING"
    BUILTIN_NATIVE_RERANKER = "BUILTIN_NATIVE_RERANKER"
    OLLAMA = "OLLAMA"
    LM_STUDIO = "LM_STUDIO"
    OPENAI_COMPATIBLE = "OPENAI_COMPATIBLE"
    LOCAL_VISION_OCR = "LOCAL_VISION_OCR"
    MOCK_SIMULATION = "MOCK_SIMULATION"


class ProviderHealthStatusEnum(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNHEALTHY = "UNHEALTHY"
    OFFLINE = "OFFLINE"


class ProviderHealthReport(BaseModel):
    """Structured report returned from passive or active provider health probes."""

    provider_name: str
    provider_type: ProviderTypeEnum
    status: ProviderHealthStatusEnum
    endpoint: Optional[str] = None
    is_live_verified: bool = False
    is_builtin: bool = False
    telemetry_exposed: bool = True
    active_model: Optional[str] = None
    available_models: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    fallback_policy: str = "FALLBACK_DISABLED"
    probe_type: str = "PASSIVE"  # "PASSIVE" or "ACTIVE"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: Dict[str, Any] = Field(default_factory=dict)


class ProviderTelemetry(BaseModel):
    """Aggregated, provider-neutral operational metrics."""

    provider_name: str
    provider_type: ProviderTypeEnum
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_latency_seconds: float = 0.0
    ttft_ms_avg: float = 0.0
    tokens_per_second_avg: float = 0.0
    last_request_timestamp: Optional[str] = None
    last_error_message: Optional[str] = None
    uptime_seconds: float = 0.0
    extension_metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def average_latency_ms(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return round((self.total_latency_seconds / self.total_requests) * 1000.0, 2)


class FallbackPolicy(BaseModel):
    """Explicit, policy-driven configuration governing provider failover."""

    policy_version: str = "v1.0"
    allow_provider_fallback: bool = False
    allow_simulation_fallback: bool = False
    max_fallback_attempts: int = 2
    task_fallback_chains: Dict[str, List[str]] = Field(
        default_factory=lambda: {
            "REASONING": ["BUILTIN_NATIVE_GGUF", "OLLAMA", "LM_STUDIO", "OPENAI_COMPATIBLE"],
            "GROUNDED_REASONING": ["BUILTIN_NATIVE_GGUF", "OLLAMA", "LM_STUDIO", "OPENAI_COMPATIBLE"],
            "STRUCTURED_EXTRACTION": ["BUILTIN_NATIVE_GGUF", "OLLAMA", "LM_STUDIO"],
            "EMBEDDING": ["BUILTIN_NATIVE_EMBEDDING", "OLLAMA", "OPENAI_COMPATIBLE"],
            "RERANKING": ["BUILTIN_NATIVE_RERANKER"],
            "TOOL_CALL": ["BUILTIN_NATIVE_GGUF", "OLLAMA"],
            "VISION_OCR": ["LOCAL_VISION_OCR"],
        }
    )


class FallbackExecutionRecord(BaseModel):
    """Audit traceability record of provider selection and any failover."""

    requested_provider: str
    actual_provider: str
    fallback_occurred: bool = False
    fallback_reason: Optional[str] = None
    fallback_chain: List[str] = Field(default_factory=list)
    policy_version: str = "v1.0"
    is_simulation: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# =============================================================================
# BASE ADAPTER ABSTRACT INTERFACE
# =============================================================================

class BaseProviderAdapter(ABC):
    """Abstract base class for all Local Provider Adapters."""

    def __init__(self, name: str, provider_type: ProviderTypeEnum, endpoint: Optional[str] = None, is_builtin: bool = False):
        self.name = name
        self.provider_type = provider_type
        self.endpoint = endpoint
        self.is_builtin = is_builtin
        self.telemetry_exposed = is_builtin  # Native engines expose rich telemetry; external daemons expose limited
        self.fallback_policy: str = "FALLBACK_DISABLED"
        self._is_simulation = False
        self._telemetry = ProviderTelemetry(provider_name=name, provider_type=provider_type)
        self._health_status = ProviderHealthStatusEnum.OFFLINE
        self._consecutive_failures = 0
        self._last_error: Optional[str] = None

    def update_endpoint(self, base_url: str, **kwargs: Any) -> None:
        """Updates the configured endpoint URL / port without requiring process restarts."""
        self.endpoint = base_url.rstrip("/")
        if hasattr(self, "base_url"):
            setattr(self, "base_url", base_url.rstrip("/"))
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    @property
    def is_simulation(self) -> bool:
        return self._is_simulation

    @property
    def telemetry(self) -> ProviderTelemetry:
        return self._telemetry

    @property
    def health_status(self) -> ProviderHealthStatusEnum:
        return self._health_status

    @abstractmethod
    def supported_tasks(self) -> List[TaskType]:
        """Returns the list of tasks supported by this provider adapter."""
        pass

    @abstractmethod
    async def passive_health_probe(self) -> ProviderHealthReport:
        """Lightweight reachability and readiness check without generating text."""
        pass

    @abstractmethod
    async def active_health_probe(self) -> ProviderHealthReport:
        """Explicit end-to-end inference verification probe."""
        pass

    @abstractmethod
    def translate_exception(self, exc: Exception, task_type: Optional[TaskType] = None, model_id: Optional[str] = None) -> AIProviderError:
        """Translates underlying driver/network exceptions into typed AIProviderError."""
        pass

    def record_success(self, latency_seconds: float, prompt_tokens: int = 0, completion_tokens: int = 0, ttft_ms: float = 0.0) -> None:
        """Updates internal telemetry metrics upon successful execution."""
        self._health_status = ProviderHealthStatusEnum.HEALTHY
        self._consecutive_failures = 0
        self._last_error = None
        self._telemetry.total_requests += 1
        self._telemetry.successful_requests += 1
        self._telemetry.total_prompt_tokens += prompt_tokens
        self._telemetry.total_completion_tokens += completion_tokens
        self._telemetry.total_latency_seconds += latency_seconds
        self._telemetry.last_request_timestamp = datetime.now(timezone.utc).isoformat()
        if ttft_ms > 0:
            if self._telemetry.ttft_ms_avg == 0:
                self._telemetry.ttft_ms_avg = ttft_ms
            else:
                self._telemetry.ttft_ms_avg = (self._telemetry.ttft_ms_avg * 0.9) + (ttft_ms * 0.1)

    def record_failure(self, error_message: str) -> None:
        """Updates telemetry and health status upon execution failure."""
        self._consecutive_failures += 1
        self._last_error = error_message
        self._health_status = ProviderHealthStatusEnum.DEGRADED if self._consecutive_failures < 3 else ProviderHealthStatusEnum.UNHEALTHY
        self._telemetry.total_requests += 1
        self._telemetry.failed_requests += 1
        self._telemetry.last_error_message = error_message
        self._telemetry.last_request_timestamp = datetime.now(timezone.utc).isoformat()


# =============================================================================
# SPECIALIZED ADAPTER PROTOCOLS
# =============================================================================

class InferenceAdapter(BaseProviderAdapter):
    """Base interface for text generation and structured reasoning providers."""

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        model_id: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
        stop: Optional[List[str]] = None,
        timeout_seconds: float = 60.0,
        grammar: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        pass

    @abstractmethod
    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model_id: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        stop: Optional[List[str]] = None,
        timeout_seconds: float = 60.0,
        grammar: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        pass

    @abstractmethod
    def cancel_current_generation(self) -> None:
        pass


class EmbeddingAdapter(BaseProviderAdapter):
    """Base interface for dense vector embedding providers."""

    @abstractmethod
    async def embed_texts(self, texts: List[str], model_id: Optional[str] = None) -> List[List[float]]:
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        pass

    @abstractmethod
    def is_normalized(self) -> bool:
        pass


class RerankerAdapter(BaseProviderAdapter):
    """Base interface for cross-encoder reranking providers."""

    @abstractmethod
    async def rerank_async(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        model_id: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        pass


class VisionOCRAdapter(BaseProviderAdapter):
    """Base interface for local Vision and OCR document processors."""

    @abstractmethod
    async def extract_text(self, document_bytes: bytes, mime_type: str, model_id: Optional[str] = None) -> str:
        pass

    @abstractmethod
    async def extract_structured(
        self, document_bytes: bytes, json_schema: Dict[str, Any], model_id: Optional[str] = None
    ) -> Dict[str, Any]:
        pass
