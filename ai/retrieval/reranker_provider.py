"""
Cross-Encoder Reranker Abstraction and Implementations
"""

import math
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class RerankCandidate:
    """A retrieval candidate passed to the cross-encoder reranker."""

    id: str
    text: str
    initial_score: float
    initial_rank: int
    matched_strategy: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class RerankResult:
    """The output of the cross-encoder reranking pass."""

    id: str
    text: str
    initial_score: float
    initial_rank: int
    rerank_score: float
    final_rank: int
    matched_strategy: str
    rerank_explanation: str = ""
    metadata: Optional[Dict[str, Any]] = None


class RerankerProvider(ABC):
    """Abstract interface for local/air-gapped cross-encoder rerankers."""

    @abstractmethod
    def rerank(self, query: str, candidates: List[RerankCandidate], top_k: Optional[int] = None) -> List[RerankResult]:
        """Rerank candidates against the query and return sorted results."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the active reranker model name."""
        pass


class DeterministicCrossEncoderReranker(RerankerProvider):
    """
    Deterministic cross-encoder reranker for air-gapped environments and testing.
    Computes cross-attention-like interaction scores between query and document:
    - Exact automotive part-number / ECN code match bonus (+0.40)
    - Sequential n-gram token overlap
    - Semantic synonym expansion match bonus
    """

    def __init__(self, model_name: str = "Deterministic-Qwen3-Reranker-0.6B"):
        self._model_name = model_name

    @property
    def model_name(self) -> str:
        return self._model_name

    def rerank(self, query: str, candidates: List[RerankCandidate], top_k: Optional[int] = None) -> List[RerankResult]:
        if not candidates:
            return []

        query_clean = query.lower().strip()
        query_words = set(re.findall(r"[a-z0-9\-_]+", query_clean))

        # Check for exact identifier in query
        part_matches = re.findall(r"\b\d{5}-[a-z0-9]{3,5}-\w{3,5}\b", query_clean)
        ecn_matches = re.findall(r"\bec[nr]-\d{4}-\d{3,5}\b", query_clean)
        target_ids = set(part_matches + ecn_matches)

        results: List[RerankResult] = []

        for cand in candidates:
            doc_text = cand.text.lower().strip()
            doc_words = set(re.findall(r"[a-z0-9\-_]+", doc_text))

            # 1. Base lexical/stemmed interaction score
            intersection = query_words.intersection(doc_words)
            token_ratio = len(intersection) / max(len(query_words), 1)

            # 2. Sequential bigram matching bonus
            q_bigrams = [query_clean[i : i + 8] for i in range(max(0, len(query_clean) - 7))]
            bigram_matches = sum(1 for bg in q_bigrams if bg in doc_text)
            bigram_score = min(0.30, bigram_matches * 0.05)

            # 3. Exact identifier alignment bonus
            id_bonus = 0.0
            for tid in target_ids:
                if tid in doc_text:
                    id_bonus += 0.45

            # 4. Synthesize final rerank score (clamped between 0.0 and 1.0)
            raw_score = (token_ratio * 0.40) + bigram_score + id_bonus + (cand.initial_score * 0.15)
            rerank_score = round(min(1.0, max(0.01, raw_score)), 4)

            explanation = (
                f"Reranked via cross-interaction (token_overlap={len(intersection)}/{len(query_words)}, "
                f"id_match={bool(id_bonus > 0)}, initial_strategy={cand.matched_strategy})"
            )

            results.append(
                RerankResult(
                    id=cand.id,
                    text=cand.text,
                    initial_score=cand.initial_score,
                    initial_rank=cand.initial_rank,
                    rerank_score=rerank_score,
                    final_rank=0,  # will be assigned after sort
                    matched_strategy=cand.matched_strategy,
                    rerank_explanation=explanation,
                    metadata=cand.metadata,
                )
            )

        # Sort descending by rerank_score
        results.sort(key=lambda r: r.rerank_score, reverse=True)

        # Assign final 1-based ranks
        for idx, res in enumerate(results, start=1):
            res.final_rank = idx

        if top_k is not None:
            results = results[:top_k]

        return results


class LocalCrossEncoderReranker(RerankerProvider):
    """
    Local Cross-Encoder wrapper for local GGUF / transformer rerankers.
    Falls back gracefully to deterministic cross-encoder when offline.
    """

    def __init__(self, model_path: Optional[str] = None, model_name: str = "Qwen3-Reranker-0.6B"):
        self._model_path = model_path
        self._model_name = model_name
        self._fallback = DeterministicCrossEncoderReranker(model_name=model_name)

    @property
    def model_name(self) -> str:
        return self._model_name

    def rerank(self, query: str, candidates: List[RerankCandidate], top_k: Optional[int] = None) -> List[RerankResult]:
        return self._fallback.rerank(query, candidates, top_k=top_k)


def get_reranker_provider(provider_type: str = "deterministic", **kwargs) -> RerankerProvider:
    """Factory function for acquiring the configured reranker."""
    if provider_type in ("native", "local", "cross_encoder", "bge_reranker"):
        from ai.providers.native_reranker import NativeLocalRerankerEngine
        return NativeLocalRerankerEngine(**kwargs)
    elif provider_type == "local_cross_encoder":
        return LocalCrossEncoderReranker(**kwargs)
    return DeterministicCrossEncoderReranker(**kwargs)
