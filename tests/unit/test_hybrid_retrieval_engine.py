"""
Unit Tests for Hybrid Retrieval Engine and Cross-Encoder Reranker
"""

import pytest
from ai.retrieval.embedding_provider import DeterministicEmbeddingProvider
from ai.retrieval.hybrid_engine import HybridRetrievalEngine, RetrievalQuery
from ai.retrieval.reranker_provider import DeterministicCrossEncoderReranker, RerankCandidate


def test_query_identifier_extraction():
    engine = HybridRetrievalEngine()

    ids1 = engine.extract_identifiers_from_query("Find optimization for 11100-KCC-900 on Splendor")
    assert ids1["part_number"] == "11100-KCC-900"
    assert ids1["model_code"] == "SPLENDOR"

    ids2 = engine.extract_identifiers_from_query("Status of change ECN-2024-0042")
    assert ids2["ecn_number"] == "ECN-2024-0042"


def test_cross_encoder_reranking_accuracy():
    reranker = DeterministicCrossEncoderReranker()
    candidates = [
        RerankCandidate(
            id="cand-1",
            text="Unrelated battery bracket design modification",
            initial_score=0.40,
            initial_rank=1,
            matched_strategy="VECTOR",
        ),
        RerankCandidate(
            id="cand-2",
            text="Reduce wall thickness of cylinder head cover 11100-KCC-900 casting",
            initial_score=0.35,
            initial_rank=2,
            matched_strategy="TRIGRAM",
        ),
    ]

    results = reranker.rerank(
        query="Decrease thickness of cylinder head cover 11100-KCC-900",
        candidates=candidates,
    )

    assert len(results) == 2
    # cand-2 has exact part number and token overlap, so it should rank 1st after reranking
    assert results[0].id == "cand-2"
    assert results[0].final_rank == 1
    assert results[0].rerank_score > results[1].rerank_score


def test_hybrid_search_rrf_scoring():
    emb_provider = DeterministicEmbeddingProvider()
    reranker = DeterministicCrossEncoderReranker()
    engine = HybridRetrievalEngine(embedding_provider=emb_provider, reranker_provider=reranker)

    records = [
        {
            "id": "rec-1",
            "entity_type": "IDEA_SUBMISSION",
            "entity_id": "idea-01",
            "text": "[VEHICLE: SPLENDOR_PLUS] [PART: 11100-KCC-900]\nReduce cylinder head cover thickness",
            "part_number": "11100-KCC-900",
            "model_code": "SPLENDOR_PLUS",
            "category": "GEOMETRY_OPTIMIZATION",
            "embedding_vector": emb_provider.embed_text("Reduce cylinder head cover thickness"),
        },
        {
            "id": "rec-2",
            "entity_type": "IDEA_SUBMISSION",
            "entity_id": "idea-02",
            "text": "[VEHICLE: XPULSE_200] [PART: 53100-KTR-900]\nHandle weight reduction on handlebar",
            "part_number": "53100-KTR-900",
            "model_code": "XPULSE_200",
            "category": "GEOMETRY_OPTIMIZATION",
            "embedding_vector": emb_provider.embed_text("Handle weight reduction on handlebar"),
        },
    ]

    # Search with exact part number
    q = RetrievalQuery(raw_query="Find idea on 11100-KCC-900", top_k=5)
    results = engine.search_corpus(q, records)

    assert len(results) >= 1
    assert results[0].part_number == "11100-KCC-900"
    assert "EXACT" in results[0].provenance_notes
