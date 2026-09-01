"""
LM Studio Local Provider Adapter
Provides optional, air-gapped integration with a locally running LM Studio daemon.
Operates strictly over localhost/intranet HTTP using OpenAI-compatible endpoints.
"""

import asyncio
import json
import time
import urllib.error
import urllib.request
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
    ProviderOOMError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)


class LMStudioProviderAdapter(InferenceAdapter):
    """
    Optional adapter for a locally running LM Studio desktop instance (default: http://127.0.0.1:1234).
    Uses standard local OpenAI-compatible endpoints (/v1/chat/completions, /v1/models).
    """

    def __init__(
        self,
        name: str = "local-lm-studio",
        base_url: str = "http://127.0.0.1:1234",
        request_timeout: float = 30.0,
    ):
        clean_base = base_url.rstrip("/")
        if clean_base.endswith("/v1"):
            clean_base = clean_base[:-3].rstrip("/")
        super().__init__(name=name, provider_type=ProviderTypeEnum.LM_STUDIO, endpoint=clean_base, is_builtin=False)
        self.base_url = clean_base
        self.request_timeout = request_timeout
        self._cancelled = False
        self._is_live_verified = False

    @property
    def openai_base_url(self) -> str:
        """Returns standard OpenAI-compatible base URL (/v1)."""
        return f"{self.base_url}/v1"

    def update_endpoint(self, base_url: str, **kwargs: Any) -> None:
        clean_base = base_url.rstrip("/")
        if clean_base.endswith("/v1"):
            clean_base = clean_base[:-3].rstrip("/")
        self.base_url = clean_base
        self.endpoint = clean_base
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def supported_tasks(self) -> List[TaskType]:
        return [
            TaskType.REASONING,
            TaskType.GROUNDED_REASONING,
            TaskType.STRUCTURED_EXTRACTION,
            TaskType.CLASSIFICATION,
            TaskType.SUMMARIZATION,
            TaskType.EMBEDDING,
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
        if isinstance(exc, urllib.error.URLError) or "connection refused" in err_msg.lower() or "cannot connect" in err_msg.lower():
            return ProviderUnavailableError(
                message=f"Local LM Studio daemon is unavailable at {self.base_url}: {err_msg}",
                provider_name=self.name,
                task_type=task_type,
                model_id=model_id,
                original_error_type=type(exc).__name__,
            )
        if "model" in err_msg.lower() and "not found" in err_msg.lower():
            return ModelNotFoundError(
                message=f"LM Studio model '{model_id}' is not loaded: {err_msg}",
                provider_name=self.name,
                model_id=model_id or "unknown",
                task_type=task_type,
                original_error_type=type(exc).__name__,
            )
        if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or "timed out" in err_msg.lower():
            return ProviderTimeoutError(
                message=f"LM Studio inference timed out on model '{model_id}': {err_msg}",
                provider_name=self.name,
                timeout_seconds=self.request_timeout,
                task_type=task_type,
                model_id=model_id,
                original_error_type=type(exc).__name__,
            )
        if "out of memory" in err_msg.lower() or "cuda oom" in err_msg.lower() or "oom" in err_msg.lower():
            return ProviderOOMError(
                message=f"LM Studio OOM on model '{model_id}': {err_msg}",
                provider_name=self.name,
                task_type=task_type,
                model_id=model_id,
                original_error_type=type(exc).__name__,
            )

        return AIProviderError(
            message=f"LM Studio provider execution error: {err_msg}",
            provider_name=self.name,
            task_type=task_type,
            model_id=model_id,
            error_class="LM_STUDIO_ERROR",
            original_error_type=type(exc).__name__,
        )

    async def passive_health_probe(self) -> ProviderHealthReport:
        """Passive check via /v1/models endpoint."""
        t0 = time.perf_counter()
        url = f"{self.openai_base_url}/models"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
                latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                self._health_status = ProviderHealthStatusEnum.HEALTHY
                self._is_live_verified = True
                return ProviderHealthReport(
                    provider_name=self.name,
                    provider_type=self.provider_type,
                    status=ProviderHealthStatusEnum.HEALTHY,
                    endpoint=self.base_url,
                    is_live_verified=True,
                    is_builtin=False,
                    telemetry_exposed=False,
                    fallback_policy=self.fallback_policy,
                    available_models=models,
                    latency_ms=latency_ms,
                    probe_type="PASSIVE",
                    details={"model_count": len(models), "openai_base_url": self.openai_base_url},
                )
        except Exception as e:
            self._health_status = ProviderHealthStatusEnum.OFFLINE
            return ProviderHealthReport(
                provider_name=self.name,
                provider_type=self.provider_type,
                status=ProviderHealthStatusEnum.OFFLINE,
                endpoint=self.base_url,
                is_live_verified=False,
                is_builtin=False,
                telemetry_exposed=False,
                fallback_policy=self.fallback_policy,
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                last_error=str(e),
                probe_type="PASSIVE",
                details={"openai_base_url": self.openai_base_url},
            )

    async def active_health_probe(self) -> ProviderHealthReport:
        """Active check sending a short completion test."""
        t0 = time.perf_counter()
        passive = await self.passive_health_probe()
        if passive.status == ProviderHealthStatusEnum.OFFLINE:
            return passive

        test_model = passive.available_models[0] if passive.available_models else "default"
        url = f"{self.openai_base_url}/chat/completions"
        try:
            payload = json.dumps({
                "model": test_model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 2,
                "temperature": 0.0,
            }).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                self.record_success(latency_seconds=latency_ms / 1000.0, prompt_tokens=1, completion_tokens=1)
                self._is_live_verified = True
                return ProviderHealthReport(
                    provider_name=self.name,
                    provider_type=self.provider_type,
                    status=ProviderHealthStatusEnum.HEALTHY,
                    endpoint=self.base_url,
                    is_live_verified=True,
                    is_builtin=False,
                    telemetry_exposed=False,
                    fallback_policy=self.fallback_policy,
                    available_models=passive.available_models,
                    latency_ms=latency_ms,
                    probe_type="ACTIVE",
                    details={"choices": len(data.get("choices", [])), "openai_base_url": self.openai_base_url, "tested_model": test_model},
                )
        except Exception as e:
            self.record_failure(str(e))
            return ProviderHealthReport(
                provider_name=self.name,
                provider_type=self.provider_type,
                status=ProviderHealthStatusEnum.UNHEALTHY,
                endpoint=self.base_url,
                is_live_verified=False,
                is_builtin=False,
                telemetry_exposed=False,
                fallback_policy=self.fallback_policy,
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                consecutive_failures=self._consecutive_failures,
                last_error=str(e),
                probe_type="ACTIVE",
                details={"openai_base_url": self.openai_base_url},
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
        url = f"{self.openai_base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False,
        }
        if stop:
            payload["stop"] = stop
        if json_schema:
            payload["response_format"] = {"type": "json_object", "schema": json_schema}

        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                text = choices[0]["message"]["content"] if choices else ""
                usage = data.get("usage", {})
                p_tokens = usage.get("prompt_tokens", max(1, len(prompt.split())))
                c_tokens = usage.get("completion_tokens", max(1, len(text.split())))
                elapsed = time.perf_counter() - t0
                self.record_success(latency_seconds=elapsed, prompt_tokens=p_tokens, completion_tokens=c_tokens)
                return text
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
        url = f"{self.openai_base_url}/chat/completions"
        self._cancelled = False
        payload: Dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if stop:
            payload["stop"] = stop
        if json_schema:
            payload["response_format"] = {"type": "json_object", "schema": json_schema}

        tokens_count = 0
        first_token_time = None
        try:
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                for line in resp:
                    if self._cancelled:
                        break
                    line_str = line.decode("utf-8").strip()
                    if not line_str or line_str == "data: [DONE]":
                        continue
                    if line_str.startswith("data: "):
                        item = json.loads(line_str[6:])
                        choices = item.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                if first_token_time is None:
                                    first_token_time = time.perf_counter()
                                tokens_count += 1
                                yield content

            elapsed = time.perf_counter() - t0
            ttft_ms = round((first_token_time - t0) * 1000.0, 2) if first_token_time else 0.0
            self.record_success(
                latency_seconds=elapsed,
                prompt_tokens=len(messages) * 10,
                completion_tokens=tokens_count,
                ttft_ms=ttft_ms,
            )
        except Exception as exc:
            translated = self.translate_exception(exc, task_type=TaskType.REASONING, model_id=model_id)
            self.record_failure(translated.message)
            raise translated from exc

    def cancel_current_generation(self) -> None:
        self._cancelled = True

    async def embed_texts(self, texts: List[str], model_id: Optional[str] = None) -> List[List[float]]:
        """Dense vector embeddings via LM Studio OpenAI-compatible /v1/embeddings endpoint."""
        target_model = model_id or "default"
        url = f"{self.openai_base_url}/embeddings"
        payload = json.dumps({"model": target_model, "input": texts}).encode("utf-8")
        t0 = time.perf_counter()
        try:
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("data", [])
                vectors = [item.get("embedding", []) for item in items]
                elapsed = time.perf_counter() - t0
                self.record_success(latency_seconds=elapsed, prompt_tokens=len(texts) * 8)
                return vectors
        except Exception as exc:
            translated = self.translate_exception(exc, task_type=TaskType.EMBEDDING, model_id=target_model)
            self.record_failure(translated.message)
            raise translated from exc
