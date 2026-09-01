"""
Ollama Local Provider Adapter
Provides optional, air-gapped integration with a locally running Ollama daemon.
Operates strictly over localhost/intranet HTTP without cloud dependencies.
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


class OllamaProviderAdapter(InferenceAdapter):
    """
    Optional adapter for a locally hosted Ollama instance (default: http://127.0.0.1:11434).
    Zero cloud dependencies; strictly local-network communication.
    """

    def __init__(
        self,
        name: str = "local-ollama",
        base_url: str = "http://127.0.0.1:11434",
        request_timeout: float = 30.0,
    ):
        super().__init__(name=name, provider_type=ProviderTypeEnum.OLLAMA, endpoint=base_url)
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout
        self._cancelled = False
        self._is_live_verified = False

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
                message=f"Local Ollama daemon is unavailable at {self.base_url}: {err_msg}",
                provider_name=self.name,
                task_type=task_type,
                model_id=model_id,
                original_error_type=type(exc).__name__,
            )
        if "model" in err_msg.lower() and ("not found" in err_msg.lower() or "try pulling" in err_msg.lower()):
            return ModelNotFoundError(
                message=f"Ollama model '{model_id}' is not installed locally: {err_msg}",
                provider_name=self.name,
                model_id=model_id or "unknown",
                task_type=task_type,
                original_error_type=type(exc).__name__,
            )
        if isinstance(exc, (TimeoutError, asyncio.TimeoutError)) or "timed out" in err_msg.lower():
            return ProviderTimeoutError(
                message=f"Ollama inference timed out on model '{model_id}': {err_msg}",
                provider_name=self.name,
                timeout_seconds=self.request_timeout,
                task_type=task_type,
                model_id=model_id,
                original_error_type=type(exc).__name__,
            )
        if "out of memory" in err_msg.lower() or "cuda oom" in err_msg.lower() or "memory" in err_msg.lower():
            return ProviderOOMError(
                message=f"Ollama OOM on model '{model_id}': {err_msg}",
                provider_name=self.name,
                task_type=task_type,
                model_id=model_id,
                original_error_type=type(exc).__name__,
            )

        return AIProviderError(
            message=f"Ollama provider execution error: {err_msg}",
            provider_name=self.name,
            task_type=task_type,
            model_id=model_id,
            error_class="OLLAMA_ERROR",
            original_error_type=type(exc).__name__,
        )

    async def passive_health_probe(self) -> ProviderHealthReport:
        """Passive reachability check via /api/tags without text generation."""
        t0 = time.perf_counter()
        url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models_raw = data.get("models", [])
                models = [m.get("name", "") for m in models_raw if m.get("name")]
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
                    details={"model_count": len(models), "models": models_raw},
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
            )

    async def active_health_probe(self) -> ProviderHealthReport:
        """Active inference probe generating a minimal test completion."""
        t0 = time.perf_counter()
        # Find an available model first
        passive = await self.passive_health_probe()
        if passive.status == ProviderHealthStatusEnum.OFFLINE or not passive.available_models:
            return passive

        test_model = passive.available_models[0]
        url = f"{self.base_url}/api/generate"
        try:
            payload = json.dumps({
                "model": test_model,
                "prompt": "ping",
                "stream": False,
                "options": {"num_predict": 2, "temperature": 0.0},
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
                    details={"response": data.get("response", ""), "tested_model": test_model},
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
        url = f"{self.base_url}/api/generate"
        options: Dict[str, Any] = {
            "num_predict": max_tokens,
            "temperature": temperature,
        }
        if stop:
            options["stop"] = stop

        req_body: Dict[str, Any] = {
            "model": model_id,
            "prompt": prompt,
            "stream": False,
            "options": options,
        }
        if json_schema or grammar:
            req_body["format"] = "json"

        try:
            data_bytes = json.dumps(req_body).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                text = result.get("response", "")
                elapsed = time.perf_counter() - t0
                prompt_tokens = result.get("prompt_eval_count", max(1, len(prompt.split())))
                eval_tokens = result.get("eval_count", max(1, len(text.split())))
                self.record_success(latency_seconds=elapsed, prompt_tokens=prompt_tokens, completion_tokens=eval_tokens)
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
        url = f"{self.base_url}/api/chat"
        self._cancelled = False
        options: Dict[str, Any] = {
            "num_predict": max_tokens,
            "temperature": temperature,
        }
        if stop:
            options["stop"] = stop

        req_body: Dict[str, Any] = {
            "model": model_id,
            "messages": messages,
            "stream": True,
            "options": options,
        }
        if json_schema or grammar:
            req_body["format"] = "json"

        tokens_count = 0
        first_token_time = None
        try:
            data_bytes = json.dumps(req_body).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                for line in resp:
                    if self._cancelled:
                        break
                    line_str = line.decode("utf-8").strip()
                    if not line_str:
                        continue
                    payload = json.loads(line_str)
                    chunk = payload.get("message", {}).get("content", "")
                    if chunk:
                        if first_token_time is None:
                            first_token_time = time.perf_counter()
                        tokens_count += 1
                        yield chunk

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
        """Dense vector embedding generation via Ollama /api/embeddings."""
        target_model = model_id or "qwen3-embedding-0.6b"
        url = f"{self.base_url}/api/embeddings"
        embeddings: List[List[float]] = []
        t0 = time.perf_counter()
        try:
            for text in texts:
                payload = json.dumps({"model": target_model, "prompt": text}).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=self.request_timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    vec = data.get("embedding", [])
                    embeddings.append(vec)
            elapsed = time.perf_counter() - t0
            self.record_success(latency_seconds=elapsed, prompt_tokens=len(texts) * 8)
            return embeddings
        except Exception as exc:
            translated = self.translate_exception(exc, task_type=TaskType.EMBEDDING, model_id=target_model)
            self.record_failure(translated.message)
            raise translated from exc
