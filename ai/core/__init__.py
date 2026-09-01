"""
Local AI Runtime Core Package
Foundational configurations, protocols, contracts, and native compatibility gates.
"""

from ai.core.config import AIRuntimeConfig, ai_settings
from ai.core.contracts import (
    AIExecutionEnvelope,
    EmbeddingEngineContract,
    InferenceEngineContract,
    LifecycleManagerContract,
    ModelManifestData,
    ModelProvenance,
    RerankerEngineContract,
    ToolRegistryContract,
    VisionOCREngineContract,
)
from ai.core.compatibility import (
    CompatibilityStatus,
    NativeCompatibilityGate,
    NativeCompatibilityReport,
    NativeStrategy,
)

__all__ = [
    "AIRuntimeConfig",
    "ai_settings",
    "AIExecutionEnvelope",
    "ModelProvenance",
    "ModelManifestData",
    "InferenceEngineContract",
    "EmbeddingEngineContract",
    "RerankerEngineContract",
    "VisionOCREngineContract",
    "LifecycleManagerContract",
    "ToolRegistryContract",
    "NativeCompatibilityGate",
    "NativeCompatibilityReport",
    "CompatibilityStatus",
    "NativeStrategy",
]
