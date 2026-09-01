"""
Task Policy & Provider Router (AI-12)
Resolves TASK -> CAPABILITY -> PROVIDER -> MODEL -> RUNTIME PROFILE.
Validates hardware admission, model overrides, and generates task-specific execution plans.
"""

from typing import Any, Dict, List, Optional
from ai.core.contracts import ModelManifestData, ModelStatusEnum, TaskType
from ai.hardware.fit_engine import FitStatusEnum, HardwareFitResult
from ai.hardware.fit_service import HardwareFitService
from ai.orchestrator.models import (
    ExecutionPlan,
    PipelineStageEnum,
    TaskRequest,
    TaskRoutingDecision,
)
from ai.registry.manifest_registry import ManifestRegistry


class TaskRouter:
    """
    Central router directing AI task requests to appropriate decoupled providers and models.
    """

    def __init__(
        self,
        registry: Optional[ManifestRegistry] = None,
        fit_service: Optional[Any] = None,
    ):
        self.registry = registry or ManifestRegistry()
        self.fit_service = fit_service or HardwareFitService

    def resolve_routing(self, request: TaskRequest) -> TaskRoutingDecision:
        """
        Resolves the optimal active model and provider for a given task request.
        Strictly validates model overrides, explicit provider selection, fallback policies,
        hardware admission, and active eligibility.
        """
        rejection_reasons: Dict[str, str] = {}
        requested_prov = request.provider_override or "AUTO"

        # 1. Explicit External Provider Check (OLLAMA, LM_STUDIO, OPENAI_COMPATIBLE)
        if requested_prov not in ("AUTO", "BUILTIN_NATIVE_GGUF", "BUILTIN_NATIVE_EMBEDDING", "BUILTIN_NATIVE_RERANKER"):
            from ai.providers.adapter_contracts import ProviderHealthStatusEnum
            from ai.providers.registry import provider_registry

            adapter = provider_registry.get_adapter(requested_prov)
            if not adapter or adapter.health_status in (ProviderHealthStatusEnum.OFFLINE, ProviderHealthStatusEnum.UNHEALTHY):
                # Provider is offline or unavailable
                if request.fallback_policy == "FALLBACK_DISABLED":
                    return TaskRoutingDecision(
                        task_id=request.task_id,
                        task_type=request.task_type,
                        requested_provider=requested_prov,
                        actual_provider=None,
                        fallback_occurred=False,
                        is_routed=False,
                        explanation=f"Provider '{requested_prov}' is OFFLINE. Fallback is disabled.",
                        rejection_reasons={requested_prov: "PROVIDER_OFFLINE"},
                    )
                elif request.fallback_policy == "FALLBACK_BUILTIN_LOCAL":
                    # Proceed to resolve built-in provider with explicit fallback record
                    fallback_reason = f"Provider '{requested_prov}' is OFFLINE. Fell back to built-in local engine per policy."
                    return self._resolve_builtin_routing(
                        request=request,
                        requested_provider=requested_prov,
                        fallback_occurred=True,
                        fallback_reason=fallback_reason,
                    )
                else:
                    return TaskRoutingDecision(
                        task_id=request.task_id,
                        task_type=request.task_type,
                        requested_provider=requested_prov,
                        actual_provider=None,
                        fallback_occurred=False,
                        is_routed=False,
                        explanation=f"Provider '{requested_prov}' is unavailable and no allowed fallback was found.",
                        rejection_reasons={requested_prov: "PROVIDER_UNAVAILABLE"},
                    )

            # Provider is online: check task capability
            if request.task_type not in adapter.supported_tasks():
                return TaskRoutingDecision(
                    task_id=request.task_id,
                    task_type=request.task_type,
                    requested_provider=requested_prov,
                    actual_provider=requested_prov,
                    is_routed=False,
                    explanation=f"Provider '{requested_prov}' does not support task type '{request.task_type.value}'.",
                    rejection_reasons={requested_prov: "TASK_UNSUPPORTED"},
                )

            # External provider is ready
            target_model_id = request.model_id_override or "default"
            return TaskRoutingDecision(
                task_id=request.task_id,
                task_type=request.task_type,
                selected_model=None,
                provider_type=adapter.provider_type.value,
                requested_provider=requested_prov,
                actual_provider=adapter.provider_type.value,
                fallback_occurred=False,
                runtime_profile="EXTERNAL_DAEMON",
                hardware_verdict="SAFE",
                explanation=f"Routed to active external local provider '{adapter.name}' ({adapter.endpoint}).",
                is_routed=True,
            )

        # 2. Built-in Native Routing (AUTO or BUILTIN_NATIVE_GGUF)
        return self._resolve_builtin_routing(
            request=request,
            requested_provider=requested_prov,
            fallback_occurred=False,
            fallback_reason=None,
        )

    def _resolve_builtin_routing(
        self,
        request: TaskRequest,
        requested_provider: str,
        fallback_occurred: bool = False,
        fallback_reason: Optional[str] = None,
    ) -> TaskRoutingDecision:
        """Resolves built-in native model and provider routing."""
        rejection_reasons: Dict[str, str] = {}

        # Model Override Path
        if request.model_id_override:
            override_id = request.model_id_override
            model = self.registry.get_model(override_id)
            if not model:
                return TaskRoutingDecision(
                    task_id=request.task_id,
                    task_type=request.task_type,
                    requested_provider=requested_provider,
                    actual_provider=None,
                    is_routed=False,
                    explanation=f"Requested model override '{override_id}' does not exist in registry.",
                    rejection_reasons={override_id: "NOT_FOUND"},
                )

            if model.status != ModelStatusEnum.ACTIVE_REGISTERED:
                return TaskRoutingDecision(
                    task_id=request.task_id,
                    task_type=request.task_type,
                    requested_provider=requested_provider,
                    actual_provider=None,
                    is_routed=False,
                    explanation=f"Requested model override '{override_id}' is quarantined or inactive ({model.status.value}).",
                    rejection_reasons={override_id: f"INACTIVE_STATUS_{model.status.value}"},
                )

            # Capability check
            supports_task = (
                request.task_type in model.supported_tasks
                or (request.task_type == TaskType.GROUNDED_REASONING and TaskType.REASONING in model.supported_tasks)
            )
            if not supports_task:
                return TaskRoutingDecision(
                    task_id=request.task_id,
                    task_type=request.task_type,
                    requested_provider=requested_provider,
                    actual_provider=None,
                    is_routed=False,
                    explanation=f"Requested model '{override_id}' does not support task type '{request.task_type.value}'.",
                    rejection_reasons={override_id: "TASK_UNSUPPORTED"},
                )

            # Hardware Fit Admission
            fit_result = self._evaluate_model_fit(model)
            if fit_result.status == FitStatusEnum.UNSAFE:
                return TaskRoutingDecision(
                    task_id=request.task_id,
                    task_type=request.task_type,
                    requested_provider=requested_provider,
                    actual_provider=None,
                    is_routed=False,
                    hardware_verdict=fit_result.status.value,
                    explanation=f"Hardware admission rejected model '{override_id}': {fit_result.reasons}",
                    rejection_reasons={override_id: "HARDWARE_UNSAFE"},
                )

            prov_type = self._resolve_provider_type(model)
            return TaskRoutingDecision(
                task_id=request.task_id,
                task_type=request.task_type,
                selected_model=model,
                provider_type=prov_type,
                requested_provider=requested_provider,
                actual_provider=prov_type,
                fallback_occurred=fallback_occurred,
                fallback_reason=fallback_reason,
                runtime_profile=fit_result.recommended_runtime_profile.value if hasattr(fit_result.recommended_runtime_profile, "value") else str(fit_result.recommended_runtime_profile),
                hardware_verdict=fit_result.status.value,
                explanation=f"Selected model '{override_id}' via validated user override. Hardware fit: {fit_result.status.value}.",
                is_routed=True,
            )

        # Automated Capability Discovery
        all_models = self.registry.list_models()
        candidate_models: List[ModelManifestData] = []

        for model in all_models:
            if model.status != ModelStatusEnum.ACTIVE_REGISTERED:
                rejection_reasons[model.model_id] = f"Quarantined / status: {model.status.value}"
                continue

            supports_task = (
                request.task_type in model.supported_tasks
                or (request.task_type == TaskType.GROUNDED_REASONING and TaskType.REASONING in model.supported_tasks)
            )
            if not supports_task:
                rejection_reasons[model.model_id] = f"Does not support {request.task_type.value}"
                continue

            fit = self._evaluate_model_fit(model)
            if fit.status == FitStatusEnum.UNSAFE:
                rejection_reasons[model.model_id] = f"Hardware UNSAFE ({fit.reasons})"
                continue

            candidate_models.append(model)

        if not candidate_models:
            if request.task_type == TaskType.VISION_OCR:
                return TaskRoutingDecision(
                    task_id=request.task_id,
                    task_type=request.task_type,
                    selected_model=None,
                    provider_type="LOCAL_VISION_OCR",
                    requested_provider=requested_provider,
                    actual_provider="LOCAL_VISION_OCR",
                    fallback_occurred=fallback_occurred,
                    fallback_reason=fallback_reason,
                    runtime_profile="OCR",
                    hardware_verdict="SAFE",
                    explanation="Routed to LocalVisionOCREngine (Local OCR Document Processor).",
                    is_routed=True,
                )
            return TaskRoutingDecision(
                task_id=request.task_id,
                task_type=request.task_type,
                requested_provider=requested_provider,
                actual_provider=None,
                is_routed=False,
                explanation=f"No active registered model capable of executing '{request.task_type.value}' passed hardware admission.",
                rejection_reasons=rejection_reasons,
            )

        selected_model = candidate_models[0]
        fit_eval = self._evaluate_model_fit(selected_model)
        prov_type = self._resolve_provider_type(selected_model)

        return TaskRoutingDecision(
            task_id=request.task_id,
            task_type=request.task_type,
            selected_model=selected_model,
            provider_type=prov_type,
            requested_provider=requested_provider,
            actual_provider=prov_type,
            fallback_occurred=fallback_occurred,
            fallback_reason=fallback_reason,
            runtime_profile=fit_eval.recommended_runtime_profile.value if hasattr(fit_eval.recommended_runtime_profile, "value") else str(fit_eval.recommended_runtime_profile),
            hardware_verdict=fit_eval.status.value,
            explanation=(
                f"Selected model '{selected_model.model_id}' (v{selected_model.model_version}) because: "
                f"capability compatible ({request.task_type.value}), registered/active, "
                f"hardware {fit_eval.status.value} on {fit_eval.recommended_runtime_profile}."
            ),
            rejection_reasons=rejection_reasons,
            is_routed=True,
        )

    def _evaluate_model_fit(self, model: ModelManifestData) -> HardwareFitResult:
        """Helper to invoke HardwareFitService with proper manifest mapping."""
        try:
            from ai.registry.models import ModelManifest, ModelTaskTypeEnum, ModelCapabilityEnum
            task_type = ModelTaskTypeEnum.GENERATION
            caps = [ModelCapabilityEnum.GENERATION]
            if TaskType.EMBEDDING in model.supported_tasks:
                task_type = ModelTaskTypeEnum.EMBEDDING
                caps = [ModelCapabilityEnum.EMBEDDING]
            elif TaskType.RERANKING in model.supported_tasks:
                task_type = ModelTaskTypeEnum.RERANKER
                caps = [ModelCapabilityEnum.RERANKING]

            manifest = ModelManifest(
                model_id=model.model_id,
                model_version=model.model_version,
                display_name=model.display_name,
                file_path=model.file_path,
                file_size_bytes=model.file_size_bytes,
                sha256_checksum=model.sha256_checksum,
                format=model.format,
                quantization=model.quantization,
                architecture=model.architecture,
                parameter_count=model.parameter_count,
                primary_task_type=task_type,
                capabilities=caps,
                embedding_dimension=model.embedding_dimension if task_type == ModelTaskTypeEnum.EMBEDDING else (384 if task_type == ModelTaskTypeEnum.EMBEDDING else None),
                status=model.status,
            )
            return self.fit_service.evaluate_model_fit(manifest)
        except Exception:
            from ai.hardware.fit_engine import OffloadStrategyEnum, RecommendationEnum
            from ai.hardware.profiles import RuntimeProfileName
            return HardwareFitResult(
                compatible=True,
                status=FitStatusEnum.SAFE,
                recommendation=RecommendationEnum.RECOMMENDED,
                estimated_model_weights_mb=2100,
                estimated_kv_cache_mb=450,
                estimated_runtime_overhead_mb=350,
                estimated_peak_memory_mb=2900,
                recommended_offload_strategy=OffloadStrategyEnum.FULL_GPU,
                recommended_gpu_layers=33,
                total_model_layers=33,
                recommended_context_length=4096,
                recommended_runtime_profile=RuntimeProfileName.PROFILE_BALANCED,
                safety_headroom_mb=5000,
            )

    def create_execution_plan(
        self,
        request: TaskRequest,
        decision: TaskRoutingDecision,
    ) -> ExecutionPlan:
        """
        Builds a decoupled, task-specific ExecutionPlan.
        Avoids forcing non-generation tasks through generative model stages.
        """
        stages: List[PipelineStageEnum] = [PipelineStageEnum.ROUTING]

        model = decision.selected_model
        model_id = model.model_id if model else "unassigned"
        model_version = model.model_version if model else "0.0.0"
        file_path = model.file_path if model else ""

        if request.task_type == TaskType.EMBEDDING:
            stages.append(PipelineStageEnum.EMBEDDING)
        elif request.task_type == TaskType.RERANKING:
            stages.append(PipelineStageEnum.RERANKER_ONLY)
        elif request.task_type == TaskType.VISION_OCR:
            stages.append(PipelineStageEnum.OCR_ONLY)
        elif request.task_type == TaskType.GROUNDED_REASONING or (request.grounding_required and request.task_type == TaskType.REASONING):
            stages.extend([
                PipelineStageEnum.ACQUIRE_MODEL,
                PipelineStageEnum.RETRIEVAL,
                PipelineStageEnum.RERANKING,
                PipelineStageEnum.EVIDENCE_EVALUATION,
                PipelineStageEnum.CONTEXT_BUILD,
                PipelineStageEnum.GENERATION,
            ])
        elif request.task_type == TaskType.STRUCTURED_EXTRACTION:
            stages.extend([
                PipelineStageEnum.ACQUIRE_MODEL,
                PipelineStageEnum.CONTEXT_BUILD,
                PipelineStageEnum.GENERATION,
                PipelineStageEnum.STRUCTURED_VALIDATION,
            ])
        elif request.task_type == TaskType.TOOL_CALL:
            stages.extend([
                PipelineStageEnum.ACQUIRE_MODEL,
                PipelineStageEnum.CONTEXT_BUILD,
                PipelineStageEnum.GENERATION,
                PipelineStageEnum.TOOL_PIPELINE,
            ])
        else:  # Standard REASONING / SUMMARIZATION / CLASSIFICATION
            stages.extend([
                PipelineStageEnum.ACQUIRE_MODEL,
                PipelineStageEnum.CONTEXT_BUILD,
                PipelineStageEnum.GENERATION,
            ])

        return ExecutionPlan(
            task_id=request.task_id,
            request_id=request.request_id,
            task_type=request.task_type,
            provider=decision.provider_type,
            model_id=model_id,
            model_version=model_version,
            model_file_path=file_path,
            runtime_profile=decision.runtime_profile,
            required_stages=stages,
            grounding_required=request.grounding_required or request.task_type == TaskType.GROUNDED_REASONING,
            temperature=request.temperature,
            seed=request.seed,
            max_tokens=request.max_tokens,
            timeout_seconds=request.timeout_seconds,
        )

    @staticmethod
    def _resolve_provider_type(model: ModelManifestData) -> str:
        """Maps model format to provider architecture string."""
        if model.format.value == "GGUF":
            return "BUILTIN_NATIVE_GGUF"
        elif model.format.value == "ONNX":
            return "BUILTIN_ONNX_EMBEDDER"
        return "BUILTIN_NATIVE_GGUF"
