"""
Native GGUF Provider Adapter
Wraps the built-in NativeGGUFEngine conforming strictly to InferenceAdapter contract.
"""

import asyncio
import time
from typing import Any, AsyncIterator, Dict, List, Optional

from ai.core.contracts import TaskType
from ai.providers.adapter_contracts import (
    InferenceAdapter,
    ProviderHealthReport,
    ProviderHealthStatusEnum,
    ProviderTypeEnum,
)
from ai.providers.exceptions import (
    AIProviderError,
    ContextOverflowError,
    ModelNotFoundError,
    ProviderCrashedError,
    ProviderOOMError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from ai.providers.native_gguf import NativeGGUFEngine, native_gguf_engine


class NativeGGUFAdapter(InferenceAdapter):
    """
    Adapter for the built-in, zero-dependency Native GGUF inference engine.
    Supports passive and active health probes, error translation, and telemetry.
    """

    def __init__(
        self,
        name: str = "builtin-native-gguf",
        engine: Optional[NativeGGUFEngine] = None,
        endpoint: Optional[str] = None,
    ):
        super().__init__(name=name, provider_type=ProviderTypeEnum.BUILTIN_NATIVE_GGUF, endpoint=endpoint, is_builtin=True)
        self.engine = engine or native_gguf_engine

    def supported_tasks(self) -> List[TaskType]:
        return [
            TaskType.REASONING,
            TaskType.GROUNDED_REASONING,
            TaskType.STRUCTURED_EXTRACTION,
            TaskType.CLASSIFICATION,
            TaskType.SUMMARIZATION,
            TaskType.TOOL_CALL,
        ]

    def translate_exception(
        self,
        exc: Exception,
        task_type: Optional[TaskType] = None,
        model_id: Optional[str] = None,
    ) -> AIProviderError:
        err_msg = str(exc)
        if isinstance(exc, AIProviderError):
            return exc
        if isinstance(exc, (asyncio.TimeoutError, TimeoutError)) or "timeout" in err_msg.lower() or "timed out" in err_msg.lower():
            return ProviderTimeoutError(
                message=f"Native GGUF execution timed out on model '{model_id}': {err_msg}",
                provider_name=self.name,
                timeout_seconds=30.0,
                task_type=task_type,
                model_id=model_id,
                original_error_type=type(exc).__name__,
            )
        if "out of memory" in err_msg.lower() or "cuda oom" in err_msg.lower() or "oom" in err_msg.lower():
            return ProviderOOMError(
                message=f"Native GGUF OOM on model '{model_id}': {err_msg}",
                provider_name=self.name,
                task_type=task_type,
                model_id=model_id,
                original_error_type=type(exc).__name__,
            )
        if "not found" in err_msg.lower() or "no model is currently loaded" in err_msg.lower() or "not registered" in err_msg.lower():
            return ModelNotFoundError(
                message=f"Native GGUF model '{model_id}' not loaded or registered: {err_msg}",
                provider_name=self.name,
                model_id=model_id or "unknown",
                task_type=task_type,
                original_error_type=type(exc).__name__,
            )
        if "context length" in err_msg.lower() or "context overflow" in err_msg.lower():
            return ContextOverflowError(
                message=f"Native GGUF context overflow on model '{model_id}': {err_msg}",
                provider_name=self.name,
                context_limit=4096,
                requested_tokens=5000,
                task_type=task_type,
                model_id=model_id,
                original_error_type=type(exc).__name__,
            )
        if "crashed" in err_msg.lower() or "process terminated" in err_msg.lower():
            return ProviderCrashedError(
                message=f"Native GGUF process crashed: {err_msg}",
                provider_name=self.name,
                task_type=task_type,
                model_id=model_id,
                original_error_type=type(exc).__name__,
            )

        return AIProviderError(
            message=f"Native GGUF execution error: {err_msg}",
            provider_name=self.name,
            task_type=task_type,
            model_id=model_id,
            error_class="NATIVE_GGUF_ERROR",
            original_error_type=type(exc).__name__,
            retryable=False,
            fallback_allowed=True,
        )

    async def passive_health_probe(self) -> ProviderHealthReport:
        """Passive check inspecting engine readiness, process state, and loaded model."""
        t0 = time.perf_counter()
        try:
            is_ready = await self.engine.is_ready()
            active_manifest = getattr(self.engine, "_active_manifest", None)
            active_model = active_manifest.model_id if active_manifest else None
            metrics = getattr(self.engine, "metrics", None)
            status = ProviderHealthStatusEnum.HEALTHY if is_ready else ProviderHealthStatusEnum.OFFLINE
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            self._health_status = status
            return ProviderHealthReport(
                provider_name=self.name,
                provider_type=self.provider_type,
                status=status,
                endpoint=self.endpoint,
                is_live_verified=True,
                is_builtin=True,
                telemetry_exposed=True,
                fallback_policy=self.fallback_policy,
                active_model=active_model,
                available_models=[active_model] if active_model else [],
                latency_ms=latency_ms,
                consecutive_failures=self._consecutive_failures,
                probe_type="PASSIVE",
                details={
                    "is_ready": is_ready,
                    "metrics": metrics.model_dump() if metrics else {},
                },
            )
        except Exception as e:
            self.record_failure(str(e))
            return ProviderHealthReport(
                provider_name=self.name,
                provider_type=self.provider_type,
                status=ProviderHealthStatusEnum.UNHEALTHY,
                endpoint=self.endpoint,
                is_live_verified=True,
                is_builtin=True,
                telemetry_exposed=True,
                fallback_policy=self.fallback_policy,
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                consecutive_failures=self._consecutive_failures,
                last_error=str(e),
                probe_type="PASSIVE",
            )

    async def active_health_probe(self) -> ProviderHealthReport:
        """Active check running a short generation prompt."""
        t0 = time.perf_counter()
        try:
            is_ready = await self.engine.is_ready()
            if not is_ready:
                return ProviderHealthReport(
                    provider_name=self.name,
                    provider_type=self.provider_type,
                    status=ProviderHealthStatusEnum.OFFLINE,
                    endpoint=self.endpoint,
                    is_live_verified=True,
                    is_builtin=True,
                    telemetry_exposed=True,
                    fallback_policy=self.fallback_policy,
                    latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                    last_error="Engine is not loaded/ready.",
                    probe_type="ACTIVE",
                )
            test_resp = await self.engine.generate_text(prompt="ping", max_tokens=2, timeout_seconds=5.0)
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            self.record_success(latency_seconds=latency_ms / 1000.0, prompt_tokens=1, completion_tokens=1)
            return ProviderHealthReport(
                provider_name=self.name,
                provider_type=self.provider_type,
                status=ProviderHealthStatusEnum.HEALTHY,
                endpoint=self.endpoint,
                is_live_verified=True,
                is_builtin=True,
                telemetry_exposed=True,
                fallback_policy=self.fallback_policy,
                latency_ms=latency_ms,
                probe_type="ACTIVE",
                details={"response": test_resp},
            )
        except Exception as e:
            self.record_failure(str(e))
            return ProviderHealthReport(
                provider_name=self.name,
                provider_type=self.provider_type,
                status=ProviderHealthStatusEnum.UNHEALTHY,
                endpoint=self.endpoint,
                is_live_verified=True,
                is_builtin=True,
                telemetry_exposed=True,
                fallback_policy=self.fallback_policy,
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                consecutive_failures=self._consecutive_failures,
                last_error=str(e),
                probe_type="ACTIVE",
            )

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
        t0 = time.perf_counter()
        try:
            # Ensure model loaded if needed
            if not await self.engine.is_ready():
                await self.engine.load_model(model_id=model_id, timeout_seconds=timeout_seconds)

            response = await self.engine.generate_text(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop,
                timeout_seconds=timeout_seconds,
                grammar=grammar,
                json_schema=json_schema,
            )
            elapsed = time.perf_counter() - t0
            prompt_est = max(1, len(prompt.split()))
            comp_est = max(1, len(response.split()))
            self.record_success(latency_seconds=elapsed, prompt_tokens=prompt_est, completion_tokens=comp_est)
            return response
        except Exception as exc:
            translated = self.translate_exception(exc, task_type=TaskType.REASONING, model_id=model_id)
            self.record_failure(translated.message)
            raise translated from exc

    async def stream_chat(
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
        t0 = time.perf_counter()
        tokens_generated = 0
        first_token_time = None
        try:
            if not await self.engine.is_ready():
                await self.engine.load_model(model_id=model_id, timeout_seconds=timeout_seconds)

            async for token in self.engine.stream_chat(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop,
                timeout_seconds=timeout_seconds,
                grammar=grammar,
                json_schema=json_schema,
            ):
                if first_token_time is None:
                    first_token_time = time.perf_counter()
                tokens_generated += 1
                yield token

            elapsed = time.perf_counter() - t0
            ttft_ms = round((first_token_time - t0) * 1000.0, 2) if first_token_time else 0.0
            self.record_success(
                latency_seconds=elapsed,
                prompt_tokens=10,
                completion_tokens=tokens_generated,
                ttft_ms=ttft_ms,
            )
        except Exception as exc:
            translated = self.translate_exception(exc, task_type=TaskType.REASONING, model_id=model_id)
            self.record_failure(translated.message)
            raise translated from exc

    def cancel_current_generation(self) -> None:
        self.engine.cancel_current_generation()
