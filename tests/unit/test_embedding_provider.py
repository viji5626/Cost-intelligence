"""
Unit Tests for Embedding Providers and Chunker
"""

import math
import pytest
from ai.retrieval.chunker import DomainChunker
from ai.retrieval.embedding_provider import (
    DeterministicEmbeddingProvider,
    LocalGGUFEmbeddingProvider,
    get_embedding_provider,
)


def test_deterministic_embedding_dimensions_and_normalization():
    provider = DeterministicEmbeddingProvider(dimension=384)
    assert provider.dimension == 384
    assert provider.model_name == "Deterministic-Qwen3-384d"

    vec = provider.embed_text("Reduce cylinder head cover thickness on Splendor Plus 11100-KCC-900")
    assert len(vec) == 384
    # Check L2 unit normalization
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-3


def test_deterministic_embedding_reproducibility():
    provider = DeterministicEmbeddingProvider(dimension=384)
    text = "Optimize center stand bracket snap fit for HF Deluxe"

    vec1 = provider.embed_text(text)
    vec2 = provider.embed_text(text)
    assert vec1 == vec2


def test_embedding_batch_processing():
    provider = get_embedding_provider("deterministic")
    texts = [
        "Find optimization for 11100-KCC-900",
        "Material change on Glamour rear brake pedal",
    ]
    batch = provider.embed_batch(texts)
    assert len(batch) == 2
    assert len(batch[0]) == 384
    assert len(batch[1]) == 384


def test_domain_chunker_idea_submission():
    chunks = DomainChunker.chunk_idea_submission(
        idea_id="idea-001",
        title="Reduce handlebar balancer weight",
        description="Replace solid bar with hollow weighted tube on 53100-KTR-900.",
        part_number="53100-KTR-900",
        model_code="XPULSE_200",
        category="GEOMETRY_OPTIMIZATION",
    )
    assert len(chunks) == 1
    chk = chunks[0]
    assert chk.entity_id == "idea-001"
    assert "[VEHICLE: XPULSE_200]" in chk.text
    assert "[PART: 53100-KTR-900]" in chk.text
    assert chk.part_number == "53100-KTR-900"


def test_domain_chunker_ecn_record():
    chunks = DomainChunker.chunk_ecn_record(
        ecn_id="ecn-001",
        ecn_number="ECN-2024-0042",
        title="Rear brake pedal bushing change",
        description="Changed bronze bushing to composite polymer.",
        part_number="46500-KTR-700",
        model_code="GLAMOUR",
    )
    assert len(chunks) == 1
    chk = chunks[0]
    assert chk.entity_type == "ECN"
    assert chk.ecn_number == "ECN-2024-0042"
    assert "[ECN: ECN-2024-0042]" in chk.text
