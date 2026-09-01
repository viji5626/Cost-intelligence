"""
Mock Simulation Provider Adapter
Dedicated test and simulation double for CI/CD, hermetic benchmarking, and air-gapped unit tests.
Isolated with explicit simulation flags so it can NEVER be silently used in production.
"""

import time
from typing import Any, AsyncIterator, Dict, List, Optional

from ai.core.contracts import TaskType
from ai.providers.adapter_contracts import (
    EmbeddingAdapter,
    InferenceAdapter,
    ProviderHealthReport,
    ProviderHealthStatusEnum,
    ProviderTypeEnum,
    RerankerAdapter,
    VisionOCRAdapter,
)
from ai.providers.exceptions import AIProviderError


class MockSimulationAdapter(InferenceAdapter, EmbeddingAdapter, RerankerAdapter, VisionOCRAdapter):
    """
    Synthetic Multi-Task Provider Adapter for fast, deterministic unit testing.
    Explicitly flags is_simulation=True on all outputs.
    """

    def __init__(self, name: str = "mock-simulation-provider"):
        super().__init__(name=name, provider_type=ProviderTypeEnum.MOCK_SIMULATION)
        self._is_simulation = True
        self._health_status = ProviderHealthStatusEnum.HEALTHY

    def supported_tasks(self) -> List[TaskType]:
        return list(TaskType)

    def translate_exception(
        self,
        exc: Exception,
        task_type: Optional[TaskType] = None,
        model_id: Optional[str] = None,
    ) -> AIProviderError:
        return AIProviderError(
            message=f"Mock simulation error: {str(exc)}",
            provider_name=self.name,
            task_type=task_type,
            model_id=model_id,
            error_class="MOCK_SIMULATION_ERROR",
            original_error_type=type(exc).__name__,
        )

    async def passive_health_probe(self) -> ProviderHealthReport:
        return ProviderHealthReport(
            provider_name=self.name,
            provider_type=self.provider_type,
            status=ProviderHealthStatusEnum.HEALTHY,
            is_live_verified=True,
            active_model="mock-sim-model-v1",
            available_models=["mock-sim-model-v1", "mock-embedding-v1", "mock-reranker-v1"],
            latency_ms=0.1,
            probe_type="PASSIVE",
            details={"is_simulation": True},
        )

    async def active_health_probe(self) -> ProviderHealthReport:
        self.record_success(latency_seconds=0.0001, prompt_tokens=1, completion_tokens=1)
        return ProviderHealthReport(
            provider_name=self.name,
            provider_type=self.provider_type,
            status=ProviderHealthStatusEnum.HEALTHY,
            is_live_verified=True,
            active_model="mock-sim-model-v1",
            latency_ms=0.1,
            probe_type="ACTIVE",
            details={"is_simulation": True},
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
        self.record_success(latency_seconds=0.001, prompt_tokens=len(prompt.split()), completion_tokens=10)
        if json_schema or grammar:
            return '{"status": "SUCCESS", "is_simulation": true, "category": "LIGHTWEIGHTING"}'
        return f"[Mock Simulation Response]: Generated text for prompt: '{prompt[:30]}...'"

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
        tokens = ["[Mock ", "Stream ", "Token 1", " Token 2]"]
        for t in tokens:
            yield t
        self.record_success(latency_seconds=0.001, prompt_tokens=10, completion_tokens=len(tokens))

    def cancel_current_generation(self) -> None:
        pass

    async def embed_texts(self, texts: List[str], model_id: Optional[str] = None) -> List[List[float]]:
        dim = self.get_dimension()
        vectors = []
        for t in texts:
            val = float(len(t) % 100) / 100.0
            vec = [val] * dim
            vectors.append(vec)
        self.record_success(latency_seconds=0.001, prompt_tokens=len(texts) * 5)
        return vectors

    def get_dimension(self) -> int:
        return 384

    def is_normalized(self) -> bool:
        return True

    async def rerank_async(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        model_id: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        results = []
        limit = top_k or len(candidates)
        for idx, c in enumerate(candidates[:limit]):
            score = round(1.0 - (idx * 0.1), 4)
            results.append({
                "id": str(c.get("id", f"c_{idx}")),
                "text": str(c.get("text", c.get("content", ""))),
                "initial_score": float(c.get("score", 0.5)),
                "initial_rank": idx + 1,
                "rerank_score": score,
                "final_rank": idx + 1,
                "matched_strategy": "MOCK_SIMULATION",
                "metadata": c.get("metadata", {}),
            })
        self.record_success(latency_seconds=0.001, prompt_tokens=len(query.split()) + len(candidates) * 5)
        return results

    async def extract_text(self, document_bytes: bytes, mime_type: str, model_id: Optional[str] = None) -> str:
        self.record_success(latency_seconds=0.001)
        return "[Mock Simulation OCR]: Extracted text from simulated document."

    async def extract_structured(
        self, document_bytes: bytes, json_schema: Dict[str, Any], model_id: Optional[str] = None
    ) -> Dict[str, Any]:
        self.record_success(latency_seconds=0.001)
        return {"status": "SUCCESS", "is_simulation": True, "extracted_fields": {"part": "53100-KTR-900"}}
