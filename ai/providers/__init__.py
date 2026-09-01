"""
AI Providers and Adapter Layer Package
Standardized provider adapters, fallback chains, registry, telemetry, and error hierarchy.
"""

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
from ai.providers.base import (
    AIProvider,
    ChatMessage,
    CompletionResponse,
    EmbeddingResponse,
    InferenceEngine,
    RerankCandidate,
    RerankResponse,
    StructuredResponse,
    ToolCall,
    ToolDefinition,
)
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
from ai.providers.mock_provider import MockAIProvider
from ai.providers.native_embedding import NativeLocalEmbeddingEngine
from ai.providers.native_gguf import NativeGGUFEngine, native_gguf_engine
from ai.providers.native_reranker import NativeLocalRerankerEngine
from ai.providers.registry import ProviderAdapterRegistry, provider_registry

__all__ = [
    # Base Protocols
    "AIProvider",
    "ChatMessage",
    "CompletionResponse",
    "EmbeddingResponse",
    "InferenceEngine",
    "RerankCandidate",
    "RerankResponse",
    "StructuredResponse",
    "ToolCall",
    "ToolDefinition",
    # Adapter Contracts & Telemetry
    "BaseProviderAdapter",
    "InferenceAdapter",
    "EmbeddingAdapter",
    "RerankerAdapter",
    "VisionOCRAdapter",
    "ProviderTypeEnum",
    "ProviderHealthStatusEnum",
    "ProviderHealthReport",
    "ProviderTelemetry",
    "FallbackPolicy",
    "FallbackExecutionRecord",
    # Exceptions
    "AIProviderError",
    "ProviderUnavailableError",
    "ModelNotFoundError",
    "ProviderTimeoutError",
    "ProviderOOMError",
    "ProviderCrashedError",
    "ContextOverflowError",
    "ProviderModelIncompatibleError",
    "InputValidationError",
    # Concrete Adapters
    "NativeGGUFAdapter",
    "NativeEmbeddingAdapter",
    "NativeRerankerAdapter",
    "OllamaProviderAdapter",
    "LMStudioProviderAdapter",
    "LocalOpenAICompatibleAdapter",
    "LocalVisionOCRAdapter",
    "MockSimulationAdapter",
    # Registry & Fallback
    "ProviderAdapterRegistry",
    "provider_registry",
    "ProviderFallbackExecutor",
    # Engines
    "NativeGGUFEngine",
    "native_gguf_engine",
    "NativeLocalEmbeddingEngine",
    "NativeLocalRerankerEngine",
    "MockAIProvider",
]
