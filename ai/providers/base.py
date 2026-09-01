"""
AI Provider and Inference Engine Base Protocol Interfaces
Extracted and standardized from proven TASC software asset architecture.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]


class CompletionResponse(BaseModel):
    content: str
    finish_reason: str = "stop"
    usage: Dict[str, int] = Field(default_factory=dict)
    tool_calls: List[ToolCall] = Field(default_factory=list)
    model: str
    latency_seconds: float = 0.0


class StructuredResponse(BaseModel):
    data: Dict[str, Any]
    raw_content: str
    model: str
    latency_seconds: float = 0.0


class EmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    model: str
    dimension: int
    latency_seconds: float = 0.0


class RerankCandidate(BaseModel):
    index: int
    text: str
    score: float


class RerankResponse(BaseModel):
    candidates: List[RerankCandidate]
    model: str
    latency_seconds: float = 0.0


@runtime_checkable
class InferenceEngine(Protocol):
    """Low-level model execution protocol (e.g. LlamaCppEngine, OllamaProvider)."""

    async def load_model(self, model_path: str, **kwargs: Any) -> bool:
        ...

    async def unload_model(self) -> bool:
        ...

    async def is_ready(self) -> bool:
        ...

    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.0,
        stop: Optional[List[str]] = None,
    ) -> str:
        ...

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        max_tokens: int = 1024,
        temperature: float = 0.0,
        tools: Optional[List[ToolDefinition]] = None,
    ) -> CompletionResponse:
        ...

    async def generate_structured(
        self,
        messages: List[ChatMessage],
        json_schema: Dict[str, Any],
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> StructuredResponse:
        ...


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for dense vector embedding generation."""

    async def embed_texts(self, texts: List[str]) -> EmbeddingResponse:
        ...

    def get_dimension(self) -> int:
        ...


@runtime_checkable
class RerankerProvider(Protocol):
    """Protocol for cross-encoder candidate re-ranking."""

    async def rerank(
        self, query: str, candidate_texts: List[str], top_k: int = 10
    ) -> RerankResponse:
        ...


@runtime_checkable
class AIProvider(Protocol):
    """Unified application gateway provider protocol."""

    async def chat(
        self,
        messages: List[ChatMessage],
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> CompletionResponse:
        ...

    async def generate_structured(
        self,
        messages: List[ChatMessage],
        json_schema: Dict[str, Any],
        temperature: float = 0.0,
    ) -> StructuredResponse:
        ...

    async def embed(self, texts: List[str]) -> EmbeddingResponse:
        ...

    async def rerank(
        self, query: str, candidate_texts: List[str], top_k: int = 10
    ) -> RerankResponse:
        ...
