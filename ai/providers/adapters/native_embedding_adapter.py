"""
Native Local Embedding Provider Adapter
Wraps NativeLocalEmbeddingEngine and DeterministicEmbeddingProvider for dense vector operations.
"""

import time
from typing import Any, Dict, List, Optional

from ai.core.contracts import TaskType
from ai.providers.adapter_contracts import (
    EmbeddingAdapter,
    ProviderHealthReport,
    ProviderHealthStatusEnum,
    ProviderTypeEnum,
)
from ai.providers.exceptions import (
    AIProviderError,
    InputValidationError,
    ModelNotFoundError,
    ProviderOOMError,
    ProviderTimeoutError,
)
from ai.providers.native_embedding import NativeLocalEmbeddingEngine
from ai.retrieval.embedding_provider import DeterministicEmbeddingProvider, EmbeddingProvider


class NativeEmbeddingAdapter(EmbeddingAdapter):
    """
    Adapter for native dense vector embedding generation.
    Supports dynamic vector dimension querying, L2 unit-norm validation, and batch chunking.
    """

    def __init__(
        self,
        name: str = "builtin-native-embedding",
        engine: Optional[EmbeddingProvider] = None,
        default_model_id: str = "qwen3-embedding-0.6b",
    ):
        super().__init__(name=name, provider_type=ProviderTypeEnum.BUILTIN_NATIVE_EMBEDDING)
        self.default_model_id = default_model_id
        self.engine = engine or DeterministicEmbeddingProvider(dimension=384, model_name=default_model_id)

    def supported_tasks(self) -> List[TaskType]:
        return [TaskType.EMBEDDING]

    def get_dimension(self) -> int:
        return self.engine.dimension

    def is_normalized(self) -> bool:
        return True

    def translate_exception(
        self,
        exc: Exception,
        task_type: Optional[TaskType] = None,
        model_id: Optional[str] = None,
    ) -> AIProviderError:
        err_msg = str(exc)
        if isinstance(exc, AIProviderError):
            return exc
        if "out of memory" in err_msg.lower() or "oom" in err_msg.lower():
            return ProviderOOMError(
                message=f"Native embedding OOM on model '{model_id}': {err_msg}",
                provider_name=self.name,
                task_type=TaskType.EMBEDDING,
                model_id=model_id,
                original_error_type=type(exc).__name__,
            )
        if "empty" in err_msg.lower() or "invalid text" in err_msg.lower():
            return InputValidationError(
                message=f"Invalid embedding input: {err_msg}",
                provider_name=self.name,
                task_type=TaskType.EMBEDDING,
                model_id=model_id,
                original_error_type=type(exc).__name__,
            )
        return AIProviderError(
            message=f"Native embedding error: {err_msg}",
            provider_name=self.name,
            task_type=TaskType.EMBEDDING,
            model_id=model_id,
            error_class="NATIVE_EMBEDDING_ERROR",
            original_error_type=type(exc).__name__,
        )

    async def passive_health_probe(self) -> ProviderHealthReport:
        t0 = time.perf_counter()
        dim = self.get_dimension()
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        self._health_status = ProviderHealthStatusEnum.HEALTHY
        return ProviderHealthReport(
            provider_name=self.name,
            provider_type=self.provider_type,
            status=ProviderHealthStatusEnum.HEALTHY,
            is_live_verified=True,
            active_model=self.engine.model_name,
            available_models=[self.engine.model_name],
            latency_ms=latency_ms,
            probe_type="PASSIVE",
            details={"dimension": dim, "is_normalized": self.is_normalized()},
        )

    async def active_health_probe(self) -> ProviderHealthReport:
        t0 = time.perf_counter()
        try:
            vec = self.engine.embed_text("probe")
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            self.record_success(latency_seconds=latency_ms / 1000.0, prompt_tokens=1)
            return ProviderHealthReport(
                provider_name=self.name,
                provider_type=self.provider_type,
                status=ProviderHealthStatusEnum.HEALTHY,
                is_live_verified=True,
                active_model=self.engine.model_name,
                latency_ms=latency_ms,
                probe_type="ACTIVE",
                details={"dimension": len(vec)},
            )
        except Exception as e:
            self.record_failure(str(e))
            return ProviderHealthReport(
                provider_name=self.name,
                provider_type=self.provider_type,
                status=ProviderHealthStatusEnum.UNHEALTHY,
                is_live_verified=True,
                latency_ms=round((time.perf_counter() - t0) * 1000.0, 2),
                last_error=str(e),
                probe_type="ACTIVE",
            )

    async def embed_texts(self, texts: List[str], model_id: Optional[str] = None) -> List[List[float]]:
        if not texts:
            return []
        t0 = time.perf_counter()
        try:
            if hasattr(self.engine, "embed_batch"):
                vectors = self.engine.embed_batch(texts)
            else:
                vectors = [self.engine.embed_text(t) for t in texts]
            elapsed = time.perf_counter() - t0
            self.record_success(latency_seconds=elapsed, prompt_tokens=len(texts) * 8)
            return vectors
        except Exception as exc:
            translated = self.translate_exception(exc, task_type=TaskType.EMBEDDING, model_id=model_id)
            self.record_failure(translated.message)
            raise translated from exc
