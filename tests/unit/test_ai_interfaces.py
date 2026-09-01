"""
Unit Tests for AI Provider Protocols and Mock Provider Implementation
"""

import pytest
from ai.providers.base import (
    AIProvider,
    ChatMessage,
)
from ai.providers.mock_provider import MockAIProvider


def test_mock_ai_provider_protocol_conformance():
    provider = MockAIProvider()
    assert isinstance(provider, AIProvider)


@pytest.mark.asyncio
async def test_mock_ai_provider_chat():
    provider = MockAIProvider()
    messages = [
        ChatMessage(role="system", content="You are an engineering assistant."),
        ChatMessage(role="user", content="Analyze cost savings for Part 12345."),
    ]
    resp = await provider.chat(messages=messages)
    assert resp.model == "mock-qwen-local"
    assert resp.content.startswith("[Mock AI Response]")
    assert resp.usage["total_tokens"] > 0


@pytest.mark.asyncio
async def test_mock_ai_provider_structured():
    provider = MockAIProvider()
    messages = [ChatMessage(role="user", content="Assess idea feasibility.")]
    schema = {
        "type": "object",
        "properties": {"decision": {"type": "string"}},
        "required": ["decision"],
    }
    resp = await provider.generate_structured(messages=messages, json_schema=schema)
    assert "decision" in resp.data
    assert resp.data["decision"] == "POTENTIAL_OPPORTUNITY"


@pytest.mark.asyncio
async def test_mock_ai_provider_embed_and_rerank():
    provider = MockAIProvider()
    texts = ["Rear fender bracket optimization", "Handlebar aluminum alloy switch"]
    
    # Embedding test
    embed_resp = await provider.embed(texts=texts)
    assert len(embed_resp.embeddings) == 2
    assert len(embed_resp.embeddings[0]) == provider.embedding_dimension

    # Reranking test
    rerank_resp = await provider.rerank(query="bracket cost", candidate_texts=texts, top_k=2)
    assert len(rerank_resp.candidates) == 2
    assert rerank_resp.candidates[0].score >= rerank_resp.candidates[1].score
