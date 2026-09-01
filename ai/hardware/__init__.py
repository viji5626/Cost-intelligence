"""
Hardware Profiling, Runtime Profiles & Fit Engine Package
"""

from ai.core.compatibility import (
    HostCpuSpecs,
    HostGpuSpecs,
    HostRamSpecs,
)
from ai.hardware.models import (
    CpuInfo,
    ExecutionMode,
    GpuInfo,
    HardwareProfile,
    HardwareResourceTier,
    RamInfo,
)
from ai.hardware.profiler import HardwareProfiler
from ai.hardware.profiles import (
    RUNTIME_PROFILES,
    ConcurrencyPolicyEnum,
    PreferredOffloadStrategy,
    RuntimeProfileName,
    RuntimeProfilePolicy,
)
from ai.hardware.kv_cache import KVCacheEstimateResult, KVCacheEstimator
from ai.hardware.fit_engine import (
    FitStatusEnum,
    HardwareFitEngine,
    HardwareFitResult,
    OffloadStrategyEnum,
    RecommendationEnum,
)
from ai.hardware.fit_service import ConcurrencyEvaluationResult, HardwareFitService

__all__ = [
    "CpuInfo",
    "RamInfo",
    "GpuInfo",
    "HardwareProfile",
    "HardwareResourceTier",
    "ExecutionMode",
    "HostCpuSpecs",
    "HostRamSpecs",
    "HostGpuSpecs",
    "HardwareProfiler",
    "RUNTIME_PROFILES",
    "RuntimeProfileName",
    "RuntimeProfilePolicy",
    "ConcurrencyPolicyEnum",
    "PreferredOffloadStrategy",
    "KVCacheEstimator",
    "KVCacheEstimateResult",
    "HardwareFitEngine",
    "HardwareFitResult",
    "FitStatusEnum",
    "OffloadStrategyEnum",
    "RecommendationEnum",
    "HardwareFitService",
    "ConcurrencyEvaluationResult",
]
