"""
Hardware Fit Engine & Admission Control Module
Calculates granular memory allocation, KV cache scaling, GPU offload layer partitioning, and fit status.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from ai.hardware.kv_cache import KVCacheEstimator
from ai.core.compatibility import HostCpuSpecs, HostGpuSpecs, HostRamSpecs
from ai.hardware.models import GpuInfo
from ai.hardware.profiles import (
    RUNTIME_PROFILES,
    PreferredOffloadStrategy,
    RuntimeProfileName,
    RuntimeProfilePolicy,
)
from ai.registry.models import ModelManifest, ModelStatusEnum, ModelTaskTypeEnum


class FitStatusEnum(str, Enum):
    SAFE = "SAFE"                  # Fits well within usable VRAM/RAM with generous safety headroom
    CAUTION = "CAUTION"            # Fits close to memory budget threshold or requires partial offload
    UNSAFE = "UNSAFE"              # Projected memory exceeds usable budget; high risk of OOM
    INCOMPATIBLE = "INCOMPATIBLE"  # Unsupported format, missing capabilities, or non-functional environment


class OffloadStrategyEnum(str, Enum):
    FULL_GPU = "FULL_GPU"          # All model layers offloaded to GPU VRAM
    PARTIAL_GPU = "PARTIAL_GPU"    # Subset of layers offloaded to VRAM; remainder on CPU/RAM
    CPU_ONLY = "CPU_ONLY"          # 100% of layers allocated in system RAM (AVX2/AVX-512)


class RecommendationEnum(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    ACCEPTABLE = "ACCEPTABLE"
    CAUTION = "CAUTION"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"
    INCOMPATIBLE = "INCOMPATIBLE"


class HardwareFitResult(BaseModel):
    """Detailed analytical evaluation produced by HardwareFitEngine."""

    # 1. Decision & Status
    compatible: bool
    status: FitStatusEnum
    recommendation: RecommendationEnum

    # 2. Hardware Resource Snapshot
    gpu_name: Optional[str] = None
    is_cuda_ready: bool = False
    total_vram_mb: int = 0
    available_vram_mb: int = 0
    usable_vram_budget_mb: int = 0
    total_ram_mb: int = 0
    available_ram_mb: int = 0
    usable_ram_budget_mb: int = 0

    # 3. Model Memory Breakdown
    estimated_model_weights_mb: int
    estimated_kv_cache_mb: int
    estimated_runtime_overhead_mb: int
    estimated_peak_memory_mb: int

    # 4. Offload & Layer Partitioning Recommendations
    recommended_offload_strategy: OffloadStrategyEnum
    recommended_gpu_layers: int
    total_model_layers: int
    recommended_context_length: int
    recommended_runtime_profile: RuntimeProfileName
    safety_headroom_mb: int

    # 5. Explanatory Diagnostics
    reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    # 6. Immutable Provenance
    provenance_snapshot: Dict[str, Any] = Field(default_factory=dict)


class HardwareFitEngine:
    """Evaluates model manifests against real or simulated hardware resources and runtime profiles."""

    RUNTIME_OVERHEAD_BASE_MB = 350  # CUDA context, CUDA scratch, graph runtime memory

    @classmethod
    def evaluate_fit(
        cls,
        manifest: ModelManifest,
        target_task: ModelTaskTypeEnum,
        gpu_info: HostGpuSpecs,
        ram_info: HostRamSpecs,
        cpu_info: HostCpuSpecs,
        context_length: Optional[int] = None,
        requested_profile: Optional[RuntimeProfileName] = None,
        active_vram_pressure_mb: int = 0,
    ) -> HardwareFitResult:
        """
        Performs holistic memory fit evaluation across VRAM, RAM, KV cache, and runtime overhead.
        """
        reasons: List[str] = []
        warnings: List[str] = []

        # 1. Task Capability Gate
        is_task_compatible = (
            manifest.primary_task_type == target_task
            or target_task.value in [c.value for c in manifest.capabilities]
        )
        if not is_task_compatible:
            return HardwareFitResult(
                compatible=False,
                status=FitStatusEnum.INCOMPATIBLE,
                recommendation=RecommendationEnum.INCOMPATIBLE,
                gpu_name=gpu_info.device_name,
                is_cuda_ready=gpu_info.cuda_driver_supported,
                total_vram_mb=int(gpu_info.total_vram_gb * 1024),
                available_vram_mb=int(gpu_info.free_vram_gb * 1024),
                usable_vram_budget_mb=0,
                total_ram_mb=int(ram_info.total_gb * 1024),
                available_ram_mb=int(ram_info.available_gb * 1024),
                usable_ram_budget_mb=0,
                estimated_model_weights_mb=int(manifest.file_size_bytes / (1024**2)),
                estimated_kv_cache_mb=0,
                estimated_runtime_overhead_mb=0,
                estimated_peak_memory_mb=0,
                recommended_offload_strategy=OffloadStrategyEnum.CPU_ONLY,
                recommended_gpu_layers=0,
                total_model_layers=36,
                recommended_context_length=0,
                recommended_runtime_profile=RuntimeProfileName.CPU_ONLY,
                safety_headroom_mb=0,
                reasons=[
                    f"Model '{manifest.model_id}' does not declare capability for task '{target_task.value}' "
                    f"(Capabilities: {[c.value for c in manifest.capabilities]})"
                ],
                warnings=warnings,
                provenance_snapshot={
                    "evaluated_at": datetime.now(timezone.utc).isoformat(),
                    "model_id": manifest.model_id,
                    "target_task": target_task.value,
                },
            )

        # 2. Context Window Resolution
        target_context = context_length or manifest.recommended_context_length or 4096
        if target_context > manifest.context_length:
            warnings.append(
                f"Requested context {target_context} exceeds model native context limit ({manifest.context_length}). "
                f"Clamping to {manifest.context_length}."
            )
            target_context = manifest.context_length

        # 3. Resolve Active Runtime Profile & Resource Budgets
        profile_name = requested_profile or RuntimeProfileName.AUTO
        if profile_name == RuntimeProfileName.AUTO:
            if gpu_info.is_available and gpu_info.total_vram_gb >= 20.0 and ram_info.total_gb >= 48.0:
                policy = RUNTIME_PROFILES[RuntimeProfileName.PROFILE_PERFORMANCE]
            elif gpu_info.is_available and gpu_info.total_vram_gb >= 11.0 and ram_info.total_gb >= 24.0:
                policy = RUNTIME_PROFILES[RuntimeProfileName.PROFILE_BALANCED]
            elif gpu_info.is_available and gpu_info.total_vram_gb >= 6.0:
                policy = RUNTIME_PROFILES[RuntimeProfileName.PROFILE_CONSTRAINED]
            else:
                policy = RUNTIME_PROFILES[RuntimeProfileName.CPU_ONLY]
        else:
            policy = RUNTIME_PROFILES.get(profile_name, RUNTIME_PROFILES[RuntimeProfileName.PROFILE_CONSTRAINED])

        # Usable memory budgets after applying profile ratios and safety margins
        total_vram_mb = int(gpu_info.total_vram_gb * 1024)
        raw_avail_vram_mb = max(0, int(gpu_info.free_vram_gb * 1024) - active_vram_pressure_mb)
        usable_vram_mb = max(0, int((raw_avail_vram_mb - policy.vram_safety_headroom_mb) * policy.vram_budget_ratio))

        total_ram_mb = int(ram_info.total_gb * 1024)
        raw_avail_ram_mb = int(ram_info.available_gb * 1024)
        usable_ram_mb = max(0, int((raw_avail_ram_mb - policy.ram_safety_headroom_mb) * policy.ram_budget_ratio))

        # 4. Calculate Memory Components
        # Weights memory
        weights_mb = manifest.estimated_vram_mb or int(manifest.file_size_bytes / (1024**2))
        if weights_mb <= 0:
            weights_mb = max(100, int(manifest.file_size_bytes / (1024**2)))

        # Analytical KV Cache Memory
        is_generative = target_task == ModelTaskTypeEnum.GENERATION
        if is_generative:
            kv_res = KVCacheEstimator.estimate_kv_cache(
                context_length=target_context,
                architecture=manifest.architecture,
                parameter_count=manifest.parameter_count,
            )
            kv_cache_mb = kv_res.estimated_kv_mb
            if kv_res.insufficient_metadata:
                warnings.append(kv_res.notes)
        else:
            # Embedding / Reranking models do not allocate generative multi-turn KV cache
            kv_cache_mb = 32

        runtime_overhead_mb = cls.RUNTIME_OVERHEAD_BASE_MB if (gpu_info.is_available and usable_vram_mb > 0) else 150
        peak_memory_req_mb = weights_mb + kv_cache_mb + runtime_overhead_mb

        # Estimate Total Layers (Default 36 for 3B, 32 for 7B/8B, 24 for 0.6B)
        total_layers = 36
        if "7B" in manifest.parameter_count.upper() or "8B" in manifest.parameter_count.upper():
            total_layers = 32
        elif "14B" in manifest.parameter_count.upper():
            total_layers = 48
        elif "0.6B" in manifest.parameter_count.upper() or "0.5B" in manifest.parameter_count.upper():
            total_layers = 24

        # 5. Determine Offload Strategy & Layer Partitioning
        if not gpu_info.is_available or usable_vram_mb <= 500 or policy.name == RuntimeProfileName.CPU_ONLY:
            # CPU Fallback Strategy
            offload_strategy = OffloadStrategyEnum.CPU_ONLY
            rec_gpu_layers = 0
            if peak_memory_req_mb <= usable_ram_mb:
                status = FitStatusEnum.SAFE
                rec = RecommendationEnum.ACCEPTABLE
                reasons.append(
                    f"GPU unavailable or bypassed. Allocated {peak_memory_req_mb} MB in system RAM (Usable RAM: {usable_ram_mb} MB)."
                )
            elif peak_memory_req_mb <= raw_avail_ram_mb:
                status = FitStatusEnum.CAUTION
                rec = RecommendationEnum.CAUTION
                reasons.append(
                    f"Allocated {peak_memory_req_mb} MB in system RAM under tight memory margins."
                )
            else:
                status = FitStatusEnum.UNSAFE
                rec = RecommendationEnum.NOT_RECOMMENDED
                reasons.append(
                    f"Insufficient RAM: Requires {peak_memory_req_mb} MB, but only {usable_ram_mb} MB available."
                )
        else:
            # GPU Candidate Strategy
            if peak_memory_req_mb <= usable_vram_mb:
                offload_strategy = OffloadStrategyEnum.FULL_GPU
                rec_gpu_layers = total_layers
                status = FitStatusEnum.SAFE
                rec = RecommendationEnum.RECOMMENDED
                reasons.append(
                    f"Full GPU Offload: Model + KV cache ({peak_memory_req_mb} MB) fits comfortably in usable VRAM budget ({usable_vram_mb} MB)."
                )
            elif weights_mb <= usable_vram_mb and policy.preferred_offload == PreferredOffloadStrategy.PARTIAL_GPU_ACCEPTABLE:
                # Partial GPU Offload
                offload_strategy = OffloadStrategyEnum.PARTIAL_GPU
                # Calculate how many layers fit in available VRAM
                layer_weight_mb = weights_mb / total_layers
                available_for_layers = usable_vram_mb - kv_cache_mb - runtime_overhead_mb
                rec_gpu_layers = max(1, min(total_layers, int(available_for_layers / layer_weight_mb)))
                status = FitStatusEnum.CAUTION
                rec = RecommendationEnum.ACCEPTABLE
                reasons.append(
                    f"Partial GPU Offload: Offloading {rec_gpu_layers}/{total_layers} layers to GPU ({usable_vram_mb} MB usable VRAM)."
                )
            elif policy.allow_cpu_fallback and peak_memory_req_mb <= usable_ram_mb:
                offload_strategy = OffloadStrategyEnum.CPU_ONLY
                rec_gpu_layers = 0
                status = FitStatusEnum.CAUTION
                rec = RecommendationEnum.ACCEPTABLE
                warnings.append(
                    f"Model exceeds VRAM budget ({peak_memory_req_mb} MB > {usable_vram_mb} MB). Falling back to CPU RAM execution."
                )
                reasons.append(f"CPU execution fallback active ({peak_memory_req_mb} MB allocated in RAM).")
            else:
                offload_strategy = OffloadStrategyEnum.CPU_ONLY
                rec_gpu_layers = 0
                status = FitStatusEnum.UNSAFE
                rec = RecommendationEnum.NOT_RECOMMENDED
                reasons.append(
                    f"Insufficient VRAM and RAM: Model requires {peak_memory_req_mb} MB (Usable VRAM: {usable_vram_mb} MB, Usable RAM: {usable_ram_mb} MB)."
                )

        if active_vram_pressure_mb > 0:
            warnings.append(f"Active external VRAM pressure detected: {active_vram_pressure_mb} MB occupied by other processes.")

        return HardwareFitResult(
            compatible=(status != FitStatusEnum.UNSAFE and status != FitStatusEnum.INCOMPATIBLE),
            status=status,
            recommendation=rec,
            gpu_name=gpu_info.device_name,
            is_cuda_ready=gpu_info.cuda_driver_supported,
            total_vram_mb=total_vram_mb,
            available_vram_mb=raw_avail_vram_mb,
            usable_vram_budget_mb=usable_vram_mb,
            total_ram_mb=total_ram_mb,
            available_ram_mb=raw_avail_ram_mb,
            usable_ram_budget_mb=usable_ram_mb,
            estimated_model_weights_mb=weights_mb,
            estimated_kv_cache_mb=kv_cache_mb,
            estimated_runtime_overhead_mb=runtime_overhead_mb,
            estimated_peak_memory_mb=peak_memory_req_mb,
            recommended_offload_strategy=offload_strategy,
            recommended_gpu_layers=rec_gpu_layers,
            total_model_layers=total_layers,
            recommended_context_length=target_context,
            recommended_runtime_profile=policy.name,
            safety_headroom_mb=policy.vram_safety_headroom_mb if gpu_info.is_available else policy.ram_safety_headroom_mb,
            reasons=reasons,
            warnings=warnings,
            provenance_snapshot={
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
                "model_id": manifest.model_id,
                "model_version": manifest.version,
                "model_sha256": manifest.sha256_checksum,
                "quantization": manifest.quantization,
                "architecture": manifest.architecture,
                "context_length": target_context,
                "runtime_profile": policy.name.value,
                "fit_engine_version": "1.0.0",
            },
        )
