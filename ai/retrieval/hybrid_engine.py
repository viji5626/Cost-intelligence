"""
Unified Hybrid Retrieval Engine
Implements multi-strategy retrieval:
Exact Identifiers + Trigram/Keyword + Metadata Filtering + Dense Vector + Reciprocal-Rank Fusion (RRF) + Cross-Encoder Reranker.
"""

import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from ai.retrieval.embedding_provider import EmbeddingProvider, get_embedding_provider
from ai.retrieval.reranker_provider import (
    DeterministicCrossEncoderReranker,
    RerankCandidate,
    RerankResult,
    RerankerProvider,
    get_reranker_provider,
)


@dataclass
class RetrievalQuery:
    """Encapsulates a search query with explicit engineering parameters."""

    raw_query: str
    target_vehicle_model: Optional[str] = None
    target_part_number: Optional[str] = None
    target_category: Optional[str] = None
    entity_type_filter: Optional[str] = None  # IDEA_SUBMISSION, ECN, PART
    top_k: int = 10
    rrf_k: int = 60
    weight_exact: float = 2.0
    weight_trigram: float = 1.0
    weight_vector: float = 1.0
    enable_reranking: bool = True
    score_threshold: float = 0.05


@dataclass
class RetrievedDocument:
    """A scored document produced by the retrieval engine with full provenance."""

    id: str
    entity_type: str
    entity_id: str
    text: str
    matched_strategy: str  # EXACT_IDENTIFIER, KEYWORD_TRIGRAM, SEMANTIC_VECTOR, HYBRID_FUSION
    score: float
    initial_rank: int
    rerank_score: Optional[float] = None
    final_rank: Optional[int] = None
    part_number: Optional[str] = None
    model_code: Optional[str] = None
    category: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance_notes: str = ""


class HybridRetrievalEngine:
    """
    Core hybrid search orchestrator.
    Combines Exact Identifier matching, Lexical Trigram search, Metadata filtering,
    and Dense Vector similarity using Reciprocal-Rank Fusion and Cross-Encoder reranking.
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        reranker_provider: Optional[RerankerProvider] = None,
    ):
        self.embedding_provider = embedding_provider or get_embedding_provider("deterministic")
        self.reranker_provider = reranker_provider or get_reranker_provider("deterministic")

    @classmethod
    def extract_identifiers_from_query(cls, query: str) -> Dict[str, Optional[str]]:
        """Extracts candidate part numbers, ECN codes, and model codes from free-text query."""
        part_match = re.search(r"\b\d{5}-[a-zA-Z0-9]{3,5}-\w{3,5}\b", query)
        ecn_match = re.search(r"\b(?:ECN|ECR)-\d{4}-\d{3,5}\b", query, re.IGNORECASE)
        model_match = re.search(r"\b(splendor|hf\s*deluxe|glamour|passion|xpulse|xtreme|vida|zoom)\b", query, re.IGNORECASE)

        return {
            "part_number": part_match.group(0).upper() if part_match else None,
            "ecn_number": ecn_match.group(0).upper() if ecn_match else None,
            "model_code": model_match.group(0).upper().replace(" ", "_") if model_match else None,
        }

    def _cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        """Calculates cosine similarity between two float vectors."""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm_a * norm_b)))

    def _trigram_similarity(self, query: str, text: str) -> float:
        """Calculates character 3-gram and token Jaccard similarity."""
        def _get_trigrams(s: str) -> Set[str]:
            s_clean = f" {s.lower().strip()} "
            return {s_clean[i : i + 3] for i in range(len(s_clean) - 2)}

        q_grams = _get_trigrams(query)
        doc_grams = _get_trigrams(text)

        if not q_grams or not doc_grams:
            return 0.0

        intersection = len(q_grams.intersection(doc_grams))
        union = len(q_grams.union(doc_grams))
        return intersection / union if union > 0 else 0.0

    def search_corpus(
        self,
        query: RetrievalQuery,
        records: List[Dict[str, Any]],
    ) -> List[RetrievedDocument]:
        """
        Executes hybrid multi-stage retrieval over a collection of indexed records.
        Each record must contain: id, entity_type, entity_id, text, part_number,
        model_code, category, embedding_vector, metadata.
        """
        if not records:
            return []

        q_ids = self.extract_identifiers_from_query(query.raw_query)
        target_part = query.target_part_number or q_ids["part_number"]
        target_ecn = q_ids["ecn_number"]
        target_model = query.target_vehicle_model or q_ids["model_code"]
        target_category = query.target_category

        # Generate query vector for dense search
        query_vector = self.embedding_provider.embed_text(query.raw_query)

        # Strategy 1: Exact Identifier Matches
        exact_ranked: List[Tuple[Dict[str, Any], float]] = []
        # Strategy 2: Trigram / Keyword Matches
        trigram_ranked: List[Tuple[Dict[str, Any], float]] = []
        # Strategy 3: Dense Vector Matches
        vector_ranked: List[Tuple[Dict[str, Any], float]] = []

        for rec in records:
            # Metadata Filter check
            if query.entity_type_filter and rec.get("entity_type") != query.entity_type_filter:
                continue
            if target_category and rec.get("category") and rec.get("category") != target_category:
                continue

            doc_text = rec.get("text", "")
            rec_part = rec.get("part_number")
            rec_ecn = rec.get("ecn_number")
            rec_model = rec.get("model_code")

            # 1. Exact Identifier Check
            is_exact = False
            exact_score = 0.0
            if target_part and rec_part and target_part.upper() == rec_part.upper():
                is_exact = True
                exact_score += 1.0
            if target_ecn and rec_ecn and target_ecn.upper() == rec_ecn.upper():
                is_exact = True
                exact_score += 1.0
            if target_model and rec_model and target_model.upper() in rec_model.upper():
                exact_score += 0.3

            if is_exact:
                exact_ranked.append((rec, exact_score))

            # 2. Trigram Keyword Check
            tri_score = self._trigram_similarity(query.raw_query, doc_text)
            if tri_score > 0.02:
                trigram_ranked.append((rec, tri_score))

            # 3. Dense Vector Similarity Check
            doc_vec = rec.get("embedding_vector")
            if doc_vec:
                vec_score = self._cosine_similarity(query_vector, doc_vec)
                if vec_score > 0.05:
                    vector_ranked.append((rec, vec_score))

        # Sort each channel descending
        exact_ranked.sort(key=lambda x: x[1], reverse=True)
        trigram_ranked.sort(key=lambda x: x[1], reverse=True)
        vector_ranked.sort(key=lambda x: x[1], reverse=True)

        # 4. Deterministic Reciprocal-Rank Fusion (RRF)
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Dict[str, Any]] = {}
        strategy_map: Dict[str, List[str]] = {}

        # Add Exact channel
        for rank, (doc, sc) in enumerate(exact_ranked, start=1):
            did = doc["id"]
            doc_map[did] = doc
            rrf_scores[did] = rrf_scores.get(did, 0.0) + (query.weight_exact / (query.rrf_k + rank))
            strategy_map.setdefault(did, []).append(f"EXACT(rank={rank},score={round(sc,2)})")

        # Add Trigram channel
        for rank, (doc, sc) in enumerate(trigram_ranked, start=1):
            did = doc["id"]
            doc_map[did] = doc
            rrf_scores[did] = rrf_scores.get(did, 0.0) + (query.weight_trigram / (query.rrf_k + rank))
            strategy_map.setdefault(did, []).append(f"TRIGRAM(rank={rank},score={round(sc,3)})")

        # Add Vector channel
        for rank, (doc, sc) in enumerate(vector_ranked, start=1):
            did = doc["id"]
            doc_map[did] = doc
            rrf_scores[did] = rrf_scores.get(did, 0.0) + (query.weight_vector / (query.rrf_k + rank))
            strategy_map.setdefault(did, []).append(f"VECTOR(rank={rank},score={round(sc,3)})")

        # Fallback if no specific channel fired: search top raw vector or trigram
        if not rrf_scores and records:
            for rec in records[: query.top_k]:
                did = rec["id"]
                doc_map[did] = rec
                rrf_scores[did] = 0.01
                strategy_map[did] = ["FALLBACK"]

        # Sort combined documents by RRF score
        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda d: rrf_scores[d], reverse=True)

        candidates_for_rerank: List[RerankCandidate] = []
        for idx, did in enumerate(sorted_doc_ids[: query.top_k * 2], start=1):
            doc = doc_map[did]
            strategies = strategy_map.get(did, [])
            cand_strategy = "HYBRID_FUSION" if len(strategies) > 1 else (strategies[0].split("(")[0] if strategies else "VECTOR")
            candidates_for_rerank.append(
                RerankCandidate(
                    id=did,
                    text=doc.get("text", ""),
                    initial_score=round(rrf_scores[did], 6),
                    initial_rank=idx,
                    matched_strategy=cand_strategy,
                    metadata=doc,
                )
            )

        # 5. Cross-Encoder Reranking
        retrieved_docs: List[RetrievedDocument] = []
        if query.enable_reranking and candidates_for_rerank:
            rerank_results = self.reranker_provider.rerank(
                query=query.raw_query,
                candidates=candidates_for_rerank,
                top_k=query.top_k,
            )
            for res in rerank_results:
                orig_doc = doc_map[res.id]
                strat_desc = " + ".join(strategy_map.get(res.id, []))
                retrieved_docs.append(
                    RetrievedDocument(
                        id=res.id,
                        entity_type=orig_doc.get("entity_type", "UNKNOWN"),
                        entity_id=orig_doc.get("entity_id", res.id),
                        text=orig_doc.get("text", ""),
                        matched_strategy=res.matched_strategy,
                        score=res.initial_score,
                        initial_rank=res.initial_rank,
                        rerank_score=res.rerank_score,
                        final_rank=res.final_rank,
                        part_number=orig_doc.get("part_number"),
                        model_code=orig_doc.get("model_code"),
                        category=orig_doc.get("category"),
                        metadata=orig_doc.get("metadata", {}),
                        provenance_notes=f"Fused via RRF: [{strat_desc}] -> {res.rerank_explanation}",
                    )
                )
        else:
            for idx, cand in enumerate(candidates_for_rerank[: query.top_k], start=1):
                orig_doc = doc_map[cand.id]
                strat_desc = " + ".join(strategy_map.get(cand.id, []))
                retrieved_docs.append(
                    RetrievedDocument(
                        id=cand.id,
                        entity_type=orig_doc.get("entity_type", "UNKNOWN"),
                        entity_id=orig_doc.get("entity_id", cand.id),
                        text=orig_doc.get("text", ""),
                        matched_strategy=cand.matched_strategy,
                        score=cand.initial_score,
                        initial_rank=cand.initial_rank,
                        rerank_score=cand.initial_score,
                        final_rank=idx,
                        part_number=orig_doc.get("part_number"),
                        model_code=orig_doc.get("model_code"),
                        category=orig_doc.get("category"),
                        metadata=orig_doc.get("metadata", {}),
                        provenance_notes=f"Fused via RRF without rerank: [{strat_desc}]",
                    )
                )

        return retrieved_docs
