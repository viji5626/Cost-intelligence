"""
OpenAI API Protocol Schemas
Standardized request and response schemas strictly adhering to the OpenAI REST specification.
Includes local model folder scanning and SafeTensors/GGUF discovery models.
"""

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ModelCard(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "hero-cost-intelligence"
    root: Optional[str] = None
    parent: Optional[str] = None
    permission: List[Dict[str, Any]] = Field(default_factory=list)
    capabilities: Optional[List[str]] = None
    context_length: Optional[int] = None
    format: Optional[str] = "GGUF"
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = 0
    quantization: Optional[str] = "Q4_K_M"
    parameter_count: Optional[str] = "3.0B"
    vram_footprint_mb: Optional[int] = 2100


class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelCard]


class ScanDirectoryRequest(BaseModel):
    directory_path: str = Field(description="Custom local folder path to scan for GGUF and SafeTensors model files")
    recursive: bool = Field(default=True, description="Whether to scan subfolders recursively")


class ScanDirectoryResponse(BaseModel):
    directory_path: str
    total_found: int
    models: List[ModelCard]


class ChatCompletionMessage(BaseModel):
    role: str
    content: Optional[Union[str, List[Dict[str, Any]]]] = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class FunctionDefinition(BaseModel):
    name: str
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class ToolDefinitionSchema(BaseModel):
    type: str = "function"
    function: FunctionDefinition


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatCompletionMessage]
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    stop: Optional[Union[str, List[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    user: Optional[str] = None
    response_format: Optional[Dict[str, Any]] = None
    seed: Optional[int] = None
    tools: Optional[List[ToolDefinitionSchema]] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None


class ChatCompletionResponseChoice(BaseModel):
    index: int = 0
    message: ChatCompletionMessage
    finish_reason: Optional[str] = "stop"


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionResponseChoice]
    usage: UsageInfo
    system_fingerprint: Optional[str] = None


class ChatCompletionChunkDelta(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ChatCompletionChunkChoice(BaseModel):
    index: int = 0
    delta: ChatCompletionChunkDelta
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[ChatCompletionChunkChoice]
    system_fingerprint: Optional[str] = None


class CompletionRequest(BaseModel):
    model: str
    prompt: Union[str, List[str]]
    max_tokens: Optional[int] = 16
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    logprobs: Optional[int] = None
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    user: Optional[str] = None
    seed: Optional[int] = None


class CompletionChoice(BaseModel):
    text: str
    index: int = 0
    logprobs: Optional[Any] = None
    finish_reason: Optional[str] = "stop"


class CompletionResponse(BaseModel):
    id: str
    object: str = "text_completion"
    created: int
    model: str
    choices: List[CompletionChoice]
    usage: UsageInfo


class EmbeddingRequest(BaseModel):
    model: str
    input: Union[str, List[str]]
    user: Optional[str] = None
    encoding_format: Optional[str] = "float"
    dimensions: Optional[int] = None


class EmbeddingData(BaseModel):
    object: str = "embedding"
    embedding: List[float]
    index: int


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: UsageInfo


class OpenAIErrorDetail(BaseModel):
    message: str
    type: str
    param: Optional[str] = None
    code: Optional[str] = None


class OpenAIErrorResponse(BaseModel):
    error: OpenAIErrorDetail
