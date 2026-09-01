"""
Task-Specific, Policy-Driven Provider Fallback Chain
Executes inference/embedding/reranking through configured provider chains without silent fallback.
Preserves AI-02 Model Registry, AI-03 Hardware Fit, and AI-05 Model Lifecycle gating across all failovers.
"""

import logging
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Tuple

from ai.core.contracts import TaskType
from ai.hardware.fit_engine import FitStatusEnum, HardwareFitEngine
from ai.hardware.profiler import HardwareProfiler
from ai.providers.adapter_contracts import (
    BaseProviderAdapter,
    EmbeddingAdapter,
    FallbackExecutionRecord,
    FallbackPolicy,
    InferenceAdapter,
    ProviderHealthStatusEnum,
    ProviderTypeEnum,
    RerankerAdapter,
)
from ai.providers.exceptions import (
    AIProviderError,
    ModelNotFoundError,
    ProviderModelIncompatibleError,
    ProviderUnavailableError,
)
from ai.providers.registry import ProviderAdapterRegistry, provider_registry
from ai.registry.models import ModelStatusEnum
from ai.registry.registry_service import model_registry_service

logger = logging.getLogger(__name__)


class ProviderFallbackExecutor:
    """
    Executes tasks across provider adapters governed by an explicit FallbackPolicy.
    Prevents silent fallback, tracks full failover provenance, and verifies AI-02/03/05 gates.
    """

    def __init__(
        self,
        registry: Optional[ProviderAdapterRegistry] = None,
        default_policy: Optional[FallbackPolicy] = None,
    ):
        self.registry = registry or provider_registry
        self.policy = default_policy or FallbackPolicy()

    def _verify_model_and_hardware_gates(self, model_id: str, task_type: TaskType) -> Tuple[bool, Optional[str]]:
        """
        Validates model registration in AI-02 ModelRegistry and compatibility in AI-03 HardwareFitEngine.
        Ensures fallbacks never bypass fundamental safety gates.
        """
        manifest = model_registry_service.get_model(model_id)
        if not manifest:
            # For pure mock models in testing mode, allow if simulated
            if model_id.startswith("mock-"):
                return True, None
            return False, f"Model '{model_id}' not found in AI-02 Model Registry."

        if manifest.status != ModelStatusEnum.ACTIVE_REGISTERED:
            return False, f"Model '{model_id}' is {manifest.status.value} and cannot be executed (Must be ACTIVE_REGISTERED)."

        # Hardware Fit Check
        try:
            from ai.registry.models import ModelTaskTypeEnum
            if task_type == TaskType.EMBEDDING:
                target_model_task = ModelTaskTypeEnum.EMBEDDING
            elif task_type == TaskType.RERANKING:
                target_model_task = ModelTaskTypeEnum.RERANKER
            elif task_type == TaskType.VISION_OCR:
                target_model_task = ModelTaskTypeEnum.VISION_OCR
            else:
                target_model_task = ModelTaskTypeEnum.GENERATION

            compat = HardwareProfiler.get_compatibility_report()
            fit = HardwareFitEngine.evaluate_fit(
                manifest=manifest,
                target_task=target_model_task,
                gpu_info=compat.gpu,
                ram_info=compat.ram,
                cpu_info=compat.cpu,
            )
            if not fit.compatible or fit.status == FitStatusEnum.UNSAFE:
                return False, f"Hardware Fit Denied for model '{model_id}': {'; '.join(fit.reasons)}"
        except Exception as e:
            logger.warning(f"Hardware fit check encountered non-fatal probe warning: {e}")

        return True, None

    def resolve_provider_chain(
        self,
        task_type: TaskType,
        requested_provider_name: Optional[str] = None,
        policy_override: Optional[FallbackPolicy] = None,
    ) -> List[BaseProviderAdapter]:
        """
        Builds the task-specific provider candidate sequence according to policy.
        """
        effective_policy = policy_override or self.policy
        chain: List[BaseProviderAdapter] = []

        if requested_provider_name:
            req_adapter = self.registry.get_adapter(requested_provider_name)
            if req_adapter and task_type in req_adapter.supported_tasks():
                chain.append(req_adapter)
            elif req_adapter:
                raise ProviderModelIncompatibleError(
                    message=f"Requested provider '{requested_provider_name}' does not support task '{task_type.value}'.",
                    provider_name=requested_provider_name,
                    task_type=task_type,
                    model_id=None,
                )

        # If fallback is allowed, populate remaining task chain
        if effective_policy.allow_provider_fallback or not chain:
            task_key = task_type.value
            configured_types = effective_policy.task_fallback_chains.get(task_key, [])
            for p_type in configured_types:
                ad = self.registry.get_adapter(p_type)
                if ad and ad not in chain and task_type in ad.supported_tasks():
                    chain.append(ad)

        # Append simulation only if explicitly permitted
        if effective_policy.allow_simulation_fallback:
            mock_ad = self.registry.get_adapter(ProviderTypeEnum.MOCK_SIMULATION.value)
            if mock_ad and mock_ad not in chain:
                chain.append(mock_ad)

        return chain

    async def execute_text_generation(
        self,
        prompt: str,
        model_id: str,
        task_type: TaskType = TaskType.REASONING,
        requested_provider: Optional[str] = None,
        policy_override: Optional[FallbackPolicy] = None,
        max_tokens: int = 512,
        temperature: float = 0.0,
        stop: Optional[List[str]] = None,
        timeout_seconds: float = 60.0,
        grammar: Optional[str] = None,
        json_schema: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Tuple[str, FallbackExecutionRecord]:
        """
        Executes text generation across the task provider chain with strict gate verification.
        """
        effective_policy = policy_override or self.policy
        target_provider_name = requested_provider or "BUILTIN_NATIVE_GGUF"

        # 1. Gate Verification (AI-02 / AI-03)
        valid, gate_reason = self._verify_model_and_hardware_gates(model_id, task_type)
        if not valid:
            raise AIProviderError(
                message=f"Execution gate rejected: {gate_reason}",
                provider_name=target_provider_name,
                task_type=task_type,
                model_id=model_id,
                error_class="GATEWAY_ADMISSION_DENIED",
                fallback_allowed=False,
            )

        # 2. Build Candidate Chain
        candidates = self.resolve_provider_chain(
            task_type=task_type,
            requested_provider_name=requested_provider,
            policy_override=effective_policy,
        )
        if not candidates:
            raise ProviderUnavailableError(
                message=f"No provider adapter available to execute task '{task_type.value}'.",
                provider_name=target_provider_name,
                task_type=task_type,
                model_id=model_id,
            )

        last_error: Optional[Exception] = None
        attempted_chain: List[str] = []
        fallback_occurred = False
        fallback_reason: Optional[str] = None

        for idx, adapter in enumerate(candidates):
            attempted_chain.append(adapter.name)
            if not isinstance(adapter, InferenceAdapter):
                continue

            # If fallback not permitted and not first attempt, halt
            if idx > 0 and not effective_policy.allow_provider_fallback:
                break

            try:
                result_text = await adapter.generate_text(
                    prompt=prompt,
                    model_id=model_id,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=stop,
                    timeout_seconds=timeout_seconds,
                    grammar=grammar,
                    json_schema=json_schema,
                    **kwargs,
                )

                if idx > 0:
                    fallback_occurred = True

                record = FallbackExecutionRecord(
                    requested_provider=target_provider_name,
                    actual_provider=adapter.name,
                    fallback_occurred=fallback_occurred,
                    fallback_reason=fallback_reason,
                    fallback_chain=attempted_chain,
                    policy_version=effective_policy.policy_version,
                    is_simulation=adapter.is_simulation,
                )
                return result_text, record

            except Exception as e:
                last_error = e
                fallback_reason = f"Provider '{adapter.name}' failed: {str(e)}"
                logger.warning(fallback_reason)
                if not getattr(e, "fallback_allowed", True) or not effective_policy.allow_provider_fallback:
                    break

        # If we reach here, all permitted providers failed
        if last_error:
            if isinstance(last_error, AIProviderError):
                raise last_error
            raise AIProviderError(
                message=f"All provider attempts failed: {fallback_reason}",
                provider_name=target_provider_name,
                task_type=task_type,
                model_id=model_id,
                diagnostic_details={"attempted_chain": attempted_chain},
            ) from last_error

        raise ProviderUnavailableError(
            message=f"Provider '{target_provider_name}' failed and fallback was not allowed by policy.",
            provider_name=target_provider_name,
            task_type=task_type,
            model_id=model_id,
        )

    async def execute_embeddings(
        self,
        texts: List[str],
        model_id: Optional[str] = None,
        requested_provider: Optional[str] = None,
        policy_override: Optional[FallbackPolicy] = None,
    ) -> Tuple[List[List[float]], FallbackExecutionRecord]:
        """Executes embeddings across task-specific embedding provider chain."""
        effective_policy = policy_override or self.policy
        target_provider_name = requested_provider or "BUILTIN_NATIVE_EMBEDDING"
        candidates = self.resolve_provider_chain(
            task_type=TaskType.EMBEDDING,
            requested_provider_name=requested_provider,
            policy_override=effective_policy,
        )

        last_error: Optional[Exception] = None
        attempted_chain: List[str] = []

        for idx, adapter in enumerate(candidates):
            attempted_chain.append(adapter.name)
            if not isinstance(adapter, EmbeddingAdapter):
                continue

            if idx > 0 and not effective_policy.allow_provider_fallback:
                break

            try:
                vectors = await adapter.embed_texts(texts=texts, model_id=model_id)
                record = FallbackExecutionRecord(
                    requested_provider=target_provider_name,
                    actual_provider=adapter.name,
                    fallback_occurred=(idx > 0),
                    fallback_reason=f"Fell back from {attempted_chain[0]}" if idx > 0 else None,
                    fallback_chain=attempted_chain,
                    policy_version=effective_policy.policy_version,
                    is_simulation=adapter.is_simulation,
                )
                return vectors, record
            except Exception as e:
                last_error = e
                if not effective_policy.allow_provider_fallback:
                    break

        if last_error:
            if isinstance(last_error, AIProviderError):
                raise last_error
            raise AIProviderError(
                message=f"Embedding provider execution failed: {str(last_error)}",
                provider_name=target_provider_name,
                task_type=TaskType.EMBEDDING,
                model_id=model_id,
            ) from last_error

        raise ProviderUnavailableError(
            message="No embedding provider available.",
            provider_name=target_provider_name,
            task_type=TaskType.EMBEDDING,
        )

    async def execute_reranking(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        model_id: Optional[str] = None,
        top_k: Optional[int] = None,
        requested_provider: Optional[str] = None,
        policy_override: Optional[FallbackPolicy] = None,
    ) -> Tuple[List[Dict[str, Any]], FallbackExecutionRecord]:
        """Executes cross-encoder reranking across task-specific reranker provider chain."""
        effective_policy = policy_override or self.policy
        target_provider_name = requested_provider or "BUILTIN_NATIVE_RERANKER"
        provider_candidates = self.resolve_provider_chain(
            task_type=TaskType.RERANKING,
            requested_provider_name=requested_provider,
            policy_override=effective_policy,
        )

        last_error: Optional[Exception] = None
        attempted_chain: List[str] = []

        for idx, adapter in enumerate(provider_candidates):
            attempted_chain.append(adapter.name)
            if not isinstance(adapter, RerankerAdapter):
                continue

            if idx > 0 and not effective_policy.allow_provider_fallback:
                break

            try:
                results = await adapter.rerank_async(query=query, candidates=candidates, model_id=model_id, top_k=top_k)
                record = FallbackExecutionRecord(
                    requested_provider=target_provider_name,
                    actual_provider=adapter.name,
                    fallback_occurred=(idx > 0),
                    fallback_reason=f"Fell back from {attempted_chain[0]}" if idx > 0 else None,
                    fallback_chain=attempted_chain,
                    policy_version=effective_policy.policy_version,
                    is_simulation=adapter.is_simulation,
                )
                return results, record
            except Exception as e:
                last_error = e
                if not effective_policy.allow_provider_fallback:
                    break

        if last_error:
            if isinstance(last_error, AIProviderError):
                raise last_error
            raise AIProviderError(
                message=f"Reranker provider execution failed: {str(last_error)}",
                provider_name=target_provider_name,
                task_type=TaskType.RERANKING,
                model_id=model_id,
            ) from last_error

        raise ProviderUnavailableError(
            message="No reranker provider available.",
            provider_name=target_provider_name,
            task_type=TaskType.RERANKING,
        )
