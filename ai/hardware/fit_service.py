"""
Hardware Fit & Admission Control Service
Provides high-level interfaces for hardware snapshot queries, model fit evaluations, concurrency gates, and candidate ranking.
"""

from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from ai.core.compatibility import NativeCompatibilityGate
from ai.hardware.fit_engine import (
    FitStatusEnum,
    HardwareFitEngine,
    HardwareFitResult,
    RecommendationEnum,
)
from ai.hardware.profiles import (
    RUNTIME_PROFILES,
    ConcurrencyPolicyEnum,
    RuntimeProfileName,
    RuntimeProfilePolicy,
)
from ai.registry.models import ModelManifest, ModelTaskTypeEnum


class ConcurrencyEvaluationResult(BaseModel):
    """Result of evaluating multiple candidate models for simultaneous co-residency."""
    is_concurrent_allowed: bool
    concurrency_policy: ConcurrencyPolicyEnum
    total_combined_vram_mb: int
    usable_vram_budget_mb: int
    total_combined_ram_mb: int
    usable_ram_budget_mb: int
    recommended_action: str  # "CO_RESIDENT", "SEQUENTIAL_SWAP", "QUEUE"
    model_evaluations: List[HardwareFitResult] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)


class HardwareFitService:
    """Orchestrates hardware fit evaluations, concurrency admission control, and candidate ranking."""

    @classmethod
    def get_hardware_snapshot(cls) -> Dict[str, Any]:
        """Returns live hardware specifications and diagnostic report."""
        report = NativeCompatibilityGate.run_preflight_gate()
        return {
            "cpu": report.cpu.model_dump(),
            "ram": report.ram.model_dump(),
            "gpu": report.gpu.model_dump(),
            "detected_hardware_tier": report.detected_hardware_tier,
            "status": report.status.value,
            "recommended_strategy": report.recommended_strategy.value,
            "warnings": report.warnings,
        }

    @classmethod
    def list_runtime_profiles(cls) -> List[RuntimeProfilePolicy]:
        """Returns all canonical runtime profiles and resource budget policies."""
        return list(RUNTIME_PROFILES.values())

    @classmethod
    def evaluate_model_fit(
        cls,
        manifest: ModelManifest,
        target_task: ModelTaskTypeEnum = ModelTaskTypeEnum.GENERATION,
        context_length: Optional[int] = None,
        requested_profile: Optional[RuntimeProfileName] = None,
        active_vram_pressure_mb: int = 0,
    ) -> HardwareFitResult:
        """Evaluates compatibility and memory fit of a single model manifest against host hardware."""
        cpu = NativeCompatibilityGate.detect_cpu()
        ram = NativeCompatibilityGate.detect_ram()
        gpu = NativeCompatibilityGate.detect_gpu()

        return HardwareFitEngine.evaluate_fit(
            manifest=manifest,
            target_task=target_task,
            gpu_info=gpu,
            ram_info=ram,
            cpu_info=cpu,
            context_length=context_length,
            requested_profile=requested_profile,
            active_vram_pressure_mb=active_vram_pressure_mb,
        )

    @classmethod
    def evaluate_concurrency_fit(
        cls,
        models_and_tasks: List[Tuple[ModelManifest, ModelTaskTypeEnum]],
        requested_profile: Optional[RuntimeProfileName] = None,
    ) -> ConcurrencyEvaluationResult:
        """
        Evaluates whether multiple models can reside concurrently in memory.
        Enforces runtime profile concurrency policy (e.g. SEQUENTIAL on 8GB VRAM).
        """
        if not models_and_tasks:
            return ConcurrencyEvaluationResult(
                is_concurrent_allowed=True,
                concurrency_policy=ConcurrencyPolicyEnum.SEQUENTIAL,
                total_combined_vram_mb=0,
                usable_vram_budget_mb=0,
                total_combined_ram_mb=0,
                usable_ram_budget_mb=0,
                recommended_action="CO_RESIDENT",
            )

        evals: List[HardwareFitResult] = []
        total_vram_needed = 0
        total_ram_needed = 0
        reasons: List[str] = []

        for manifest, task in models_and_tasks:
            res = cls.evaluate_model_fit(
                manifest=manifest,
                target_task=task,
                requested_profile=requested_profile,
            )
            evals.append(res)
            total_vram_needed += res.estimated_peak_memory_mb
            total_ram_needed += res.estimated_peak_memory_mb

        first_eval = evals[0]
        active_profile = first_eval.recommended_runtime_profile
        policy = RUNTIME_PROFILES.get(active_profile, RUNTIME_PROFILES[RuntimeProfileName.PROFILE_CONSTRAINED])

        # Check Concurrency Policy Gate
        if policy.concurrency_policy == ConcurrencyPolicyEnum.SEQUENTIAL and len(models_and_tasks) > 1:
            reasons.append(
                f"Runtime profile '{policy.name.value}' enforces strictly SEQUENTIAL model swapping. "
                "Co-residency denied to safeguard VRAM stability."
            )
            return ConcurrencyEvaluationResult(
                is_concurrent_allowed=False,
                concurrency_policy=policy.concurrency_policy,
                total_combined_vram_mb=total_vram_needed,
                usable_vram_budget_mb=first_eval.usable_vram_budget_mb,
                total_combined_ram_mb=total_ram_needed,
                usable_ram_budget_mb=first_eval.usable_ram_budget_mb,
                recommended_action="SEQUENTIAL_SWAP",
                model_evaluations=evals,
                reasons=reasons,
            )

        # Check Combined VRAM Budget
        if first_eval.usable_vram_budget_mb > 0 and total_vram_needed <= first_eval.usable_vram_budget_mb:
            reasons.append(
                f"Combined memory ({total_vram_needed} MB) fits comfortably within usable VRAM budget ({first_eval.usable_vram_budget_mb} MB)."
            )
            return ConcurrencyEvaluationResult(
                is_concurrent_allowed=True,
                concurrency_policy=policy.concurrency_policy,
                total_combined_vram_mb=total_vram_needed,
                usable_vram_budget_mb=first_eval.usable_vram_budget_mb,
                total_combined_ram_mb=total_ram_needed,
                usable_ram_budget_mb=first_eval.usable_ram_budget_mb,
                recommended_action="CO_RESIDENT",
                model_evaluations=evals,
                reasons=reasons,
            )

        reasons.append(
            f"Combined memory requirement ({total_vram_needed} MB) exceeds usable VRAM budget ({first_eval.usable_vram_budget_mb} MB)."
        )
        return ConcurrencyEvaluationResult(
            is_concurrent_allowed=False,
            concurrency_policy=policy.concurrency_policy,
            total_combined_vram_mb=total_vram_needed,
            usable_vram_budget_mb=first_eval.usable_vram_budget_mb,
            total_combined_ram_mb=total_ram_needed,
            usable_ram_budget_mb=first_eval.usable_ram_budget_mb,
            recommended_action="SEQUENTIAL_SWAP",
            model_evaluations=evals,
            reasons=reasons,
        )

    @classmethod
    def rank_candidate_models(
        cls,
        candidates: List[ModelManifest],
        target_task: ModelTaskTypeEnum = ModelTaskTypeEnum.GENERATION,
        context_length: Optional[int] = None,
        requested_profile: Optional[RuntimeProfileName] = None,
    ) -> List[Tuple[ModelManifest, HardwareFitResult]]:
        """Ranks candidate models from best fit to incompatible for a specific task and context window."""
        results: List[Tuple[ModelManifest, HardwareFitResult]] = []

        for m in candidates:
            fit = cls.evaluate_model_fit(
                manifest=m,
                target_task=target_task,
                context_length=context_length,
                requested_profile=requested_profile,
            )
            results.append((m, fit))

        # Sort order: RECOMMENDED > ACCEPTABLE > CAUTION > NOT_RECOMMENDED > INCOMPATIBLE
        rank_order = {
            RecommendationEnum.RECOMMENDED: 0,
            RecommendationEnum.ACCEPTABLE: 1,
            RecommendationEnum.CAUTION: 2,
            RecommendationEnum.NOT_RECOMMENDED: 3,
            RecommendationEnum.INCOMPATIBLE: 4,
        }

        results.sort(key=lambda item: (rank_order.get(item[1].recommendation, 99), -item[1].estimated_peak_memory_mb))
        return results
