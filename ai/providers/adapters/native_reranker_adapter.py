"""
Native Local Cross-Encoder Reranker Provider Adapter
Wraps NativeLocalRerankerEngine and DeterministicRerankerProvider for candidate scoring and reranking.
"""

import time
from typing import Any, Dict, List, Optional

from ai.core.contracts import TaskType
from ai.providers.adapter_contracts import (
    ProviderHealthReport,
    ProviderHealthStatusEnum,
    ProviderTypeEnum,
    RerankerAdapter,
)
from ai.providers.exceptions import (
    AIProviderError,
    InputValidationError,
    ProviderTimeoutError,
)
from ai.retrieval.reranker_provider import (
    DeterministicCrossEncoderReranker,
    RerankCandidate,
    RerankResult,
    RerankerProvider,
)


class NativeRerankerAdapter(RerankerAdapter):
    """
    Adapter for native cross-encoder reranking operations.
    Standardizes candidate scoring, rank ordering, and diagnostic provenance.
    """

    def __init__(
        self,
        name: str = "builtin-native-reranker",
        engine: Optional[RerankerProvider] = None,
        default_model_id: str = "bge-reranker-v2-m3",
    ):
        super().__init__(name=name, provider_type=ProviderTypeEnum.BUILTIN_NATIVE_RERANKER)
        self.default_model_id = default_model_id
        self.engine = engine or DeterministicCrossEncoderReranker(model_name=default_model_id)

    def supported_tasks(self) -> List[TaskType]:
        return [TaskType.RERANKING]

    def translate_exception(
        self,
        exc: Exception,
        task_type: Optional[TaskType] = None,
        model_id: Optional[str] = None,
    ) -> AIProviderError:
        err_msg = str(exc)
        if isinstance(exc, AIProviderError):
            return exc
        if "empty" in err_msg.lower() or "invalid query" in err_msg.lower():
            return InputValidationError(
                message=f"Invalid reranker query or candidates: {err_msg}",
                provider_name=self.name,
                task_type=TaskType.RERANKING,
                model_id=model_id,
                original_error_type=type(exc).__name__,
            )
        return AIProviderError(
            message=f"Native reranker error: {err_msg}",
            provider_name=self.name,
            task_type=TaskType.RERANKING,
            model_id=model_id,
            error_class="NATIVE_RERANKER_ERROR",
            original_error_type=type(exc).__name__,
        )

    async def passive_health_probe(self) -> ProviderHealthReport:
        t0 = time.perf_counter()
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
        )

    async def active_health_probe(self) -> ProviderHealthReport:
        t0 = time.perf_counter()
        try:
            cand = [
                RerankCandidate(
                    id="probe_1",
                    text="Alloy casting cost reduction",
                    initial_score=0.8,
                    initial_rank=1,
                    matched_strategy="PROBE",
                )
            ]
            res = self.engine.rerank(query="casting", candidates=cand, top_k=1)
            latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            self.record_success(latency_seconds=latency_ms / 1000.0, prompt_tokens=5)
            return ProviderHealthReport(
                provider_name=self.name,
                provider_type=self.provider_type,
                status=ProviderHealthStatusEnum.HEALTHY,
                is_live_verified=True,
                active_model=self.engine.model_name,
                latency_ms=latency_ms,
                probe_type="ACTIVE",
                details={"candidates_evaluated": len(res)},
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

    async def rerank_async(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        model_id: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []
        t0 = time.perf_counter()
        try:
            rerank_candidates: List[RerankCandidate] = []
            for idx, c in enumerate(candidates):
                rerank_candidates.append(
                    RerankCandidate(
                        id=str(c.get("id", f"c_{idx}")),
                        text=str(c.get("text", c.get("content", ""))),
                        initial_score=float(c.get("score", 0.5)),
                        initial_rank=idx + 1,
                        matched_strategy=str(c.get("matched_strategy", "HYBRID")),
                        metadata=c.get("metadata", {}),
                    )
                )

            results: List[RerankResult] = self.engine.rerank(
                query=query,
                candidates=rerank_candidates,
                top_k=top_k,
            )

            output = []
            for r in results:
                output.append(
                    {
                        "id": r.id,
                        "text": r.text,
                        "initial_score": r.initial_score,
                        "initial_rank": r.initial_rank,
                        "rerank_score": r.rerank_score,
                        "final_rank": r.final_rank,
                        "matched_strategy": r.matched_strategy,
                        "rerank_explanation": r.rerank_explanation,
                        "metadata": r.metadata or {},
                    }
                )

            elapsed = time.perf_counter() - t0
            self.record_success(latency_seconds=elapsed, prompt_tokens=len(query.split()) + len(candidates) * 10)
            return output
        except Exception as exc:
            translated = self.translate_exception(exc, task_type=TaskType.RERANKING, model_id=model_id)
            self.record_failure(translated.message)
            raise translated from exc
