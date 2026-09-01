"""
Mock AI Provider
Deterministic synthetic provider used for offline Phase 0 validation and automated unit testing.
"""

from typing import Any, Dict, List, Optional
from ai.providers.base import (
    AIProvider,
    ChatMessage,
    CompletionResponse,
    EmbeddingResponse,
    RerankCandidate,
    RerankResponse,
    StructuredResponse,
)


class MockAIProvider:
    """Mock implementation of the AIProvider protocol for tests."""

    def __init__(self, model_name: str = "mock-qwen-local"):
        self.model_name = model_name
        self.embedding_dimension = 384

    async def chat(
        self,
        messages: List[ChatMessage],
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> CompletionResponse:
        last_msg = messages[-1].content if messages else "No content"
        return CompletionResponse(
            content=f"[Mock AI Response]: Processed prompt '{last_msg[:40]}...'",
            finish_reason="stop",
            usage={"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
            model=self.model_name,
            latency_seconds=0.01,
        )

    async def generate_structured(
        self,
        messages: List[ChatMessage],
        json_schema: Dict[str, Any],
        temperature: float = 0.0,
    ) -> StructuredResponse:
        # Generate a compliant deterministic mock payload
        mock_payload: Dict[str, Any] = {
            "decision": "POTENTIAL_OPPORTUNITY",
            "confidence_level": "HIGH",
            "summary": "Mock structured reasoning output",
            "evidence_grounded": True,
        }
        return StructuredResponse(
            data=mock_payload,
            raw_content='{"decision": "POTENTIAL_OPPORTUNITY", "confidence_level": "HIGH"}',
            model=self.model_name,
            latency_seconds=0.02,
        )

    async def embed(self, texts: List[str]) -> EmbeddingResponse:
        # Deterministic pseudo-embeddings of dimension 384
        vectors: List[List[float]] = []
        for text in texts:
            val = float(len(text) % 100) / 100.0
            vec = [val] * self.embedding_dimension
            vectors.append(vec)

        return EmbeddingResponse(
            embeddings=vectors,
            model="mock-qwen3-embedding",
            dimension=self.embedding_dimension,
            latency_seconds=0.005,
        )

    async def rerank(
        self, query: str, candidate_texts: List[str], top_k: int = 10
    ) -> RerankResponse:
        candidates = []
        for idx, text in enumerate(candidate_texts[:top_k]):
            score = 1.0 - (idx * 0.05)
            candidates.append(
                RerankCandidate(index=idx, text=text, score=round(max(0.1, score), 4))
            )

        return RerankResponse(
            candidates=candidates,
            model="mock-qwen3-reranker",
            latency_seconds=0.01,
        )


# Verify protocol compliance at import time
_mock_instance: AIProvider = MockAIProvider()
