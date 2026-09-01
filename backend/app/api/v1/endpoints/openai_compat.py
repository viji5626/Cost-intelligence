"""
OpenAI-Compatible REST API Router (AI-14)
Implements standard /v1 endpoints for local developer tooling (Continue, Cline, Aider, Open WebUI).
"""

from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from ai.api.openai_schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    CompletionRequest,
    CompletionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    ModelCard,
    ModelListResponse,
    ScanDirectoryRequest,
    ScanDirectoryResponse,
)
from ai.api.openai_service import openai_service
from backend.app.core.logging import logger

router = APIRouter(tags=["Local OpenAI API"])


# =============================================================================
# MODEL DISCOVERY & LOCAL FOLDER SCANNING
# =============================================================================

@router.get("/models", response_model=ModelListResponse)
async def list_models(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> ModelListResponse:
    """Lists registered, active models available for inference."""
    client_host = request.client.host if request.client else "127.0.0.1"
    openai_service.authenticate_request(authorization, client_host)
    return openai_service.list_models()


@router.post("/models/scan", response_model=ScanDirectoryResponse)
async def scan_models_in_directory(
    scan_req: ScanDirectoryRequest,
    request: Request,
    authorization: Optional[str] = Header(None),
) -> ScanDirectoryResponse:
    """
    Scans any custom local folder on disk for GGUF, SafeTensors, and ONNX models.
    Supports browsing models from custom folders, HuggingFace cache, Ollama, and LM Studio directories.
    """
    client_host = request.client.host if request.client else "127.0.0.1"
    openai_service.authenticate_request(authorization, client_host)
    return openai_service.scan_directory(scan_req.directory_path, recursive=scan_req.recursive)


@router.get("/models/{model_id:path}", response_model=ModelCard)
async def get_model(
    model_id: str,
    request: Request,
    authorization: Optional[str] = Header(None),
) -> ModelCard:
    """Retrieves metadata for a specific active model."""
    client_host = request.client.host if request.client else "127.0.0.1"
    openai_service.authenticate_request(authorization, client_host)
    return openai_service.get_model(model_id)


# =============================================================================
# CHAT COMPLETIONS
# =============================================================================

@router.post("/chat/completions")
async def create_chat_completion(
    chat_request: ChatCompletionRequest,
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """
    Standard OpenAI chat completions endpoint.
    Supports both non-streaming JSON and streaming SSE token delivery.
    """
    client_host = request.client.host if request.client else "127.0.0.1"
    openai_service.authenticate_request(authorization, client_host)

    if chat_request.stream:
        return StreamingResponse(
            openai_service.stream_chat_completion(chat_request, request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    res, headers = await openai_service.create_chat_completion(chat_request)
    return JSONResponse(content=res.model_dump(), headers=headers)


# =============================================================================
# LEGACY TEXT COMPLETIONS
# =============================================================================

@router.post("/completions")
async def create_completion(
    completion_request: CompletionRequest,
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """Legacy text completion endpoint routed through AI-12 Orchestrator."""
    client_host = request.client.host if request.client else "127.0.0.1"
    openai_service.authenticate_request(authorization, client_host)

    res, headers = await openai_service.create_completion(completion_request)
    return JSONResponse(content=res.model_dump(), headers=headers)


# =============================================================================
# DENSE EMBEDDINGS
# =============================================================================

@router.post("/embeddings")
async def create_embeddings(
    embedding_request: EmbeddingRequest,
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """Dense vector embedding endpoint strictly routed via AI-06 engine."""
    client_host = request.client.host if request.client else "127.0.0.1"
    openai_service.authenticate_request(authorization, client_host)

    res, headers = await openai_service.create_embeddings(embedding_request)
    return JSONResponse(content=res.model_dump(), headers=headers)


# =============================================================================
# PROVIDER ADAPTERS & ENDPOINT CONFIGURATION
# =============================================================================

@router.get("/providers")
async def list_providers(
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """Lists registered AI provider adapters, their configured endpoints, health status, and fallback policies."""
    client_host = request.client.host if request.client else "127.0.0.1"
    openai_service.authenticate_request(authorization, client_host)
    from ai.providers.registry import provider_registry

    providers_data = []
    for adapter in provider_registry.list_adapters():
        providers_data.append({
            "name": adapter.name,
            "provider_type": adapter.provider_type.value,
            "endpoint": adapter.endpoint,
            "health_status": adapter.health_status.value,
            "is_builtin": getattr(adapter, "is_builtin", False),
            "telemetry_exposed": getattr(adapter, "telemetry_exposed", False),
            "fallback_policy": getattr(adapter, "fallback_policy", "FALLBACK_DISABLED"),
            "supported_tasks": [t.value for t in adapter.supported_tasks()],
        })
    return JSONResponse(content={"providers": providers_data})


@router.post("/providers/{provider_id}/test")
@router.get("/providers/{provider_id}/test")
async def test_provider_connection(
    provider_id: str,
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """Tests live connection to a specified local provider adapter."""
    client_host = request.client.host if request.client else "127.0.0.1"
    openai_service.authenticate_request(authorization, client_host)
    from ai.providers.registry import provider_registry

    report = await provider_registry.test_connection(provider_id)
    return JSONResponse(content=report.model_dump())


@router.post("/providers/{provider_id}/config")
async def update_provider_configuration(
    provider_id: str,
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """Updates provider endpoint URL / port and fallback policy."""
    client_host = request.client.host if request.client else "127.0.0.1"
    openai_service.authenticate_request(authorization, client_host)
    from ai.providers.registry import provider_registry

    body = await request.json()
    endpoint = body.get("endpoint")
    fallback_policy = body.get("fallback_policy")
    api_key = body.get("api_key")

    if not endpoint:
        raise HTTPException(status_code=400, detail="Missing required 'endpoint' field.")

    adapter = provider_registry.update_provider_config(
        provider_name_or_type=provider_id,
        endpoint=endpoint,
        fallback_policy=fallback_policy,
        api_key=api_key,
    )
    return JSONResponse(content={
        "status": "UPDATED",
        "provider": adapter.name,
        "endpoint": adapter.endpoint,
        "fallback_policy": getattr(adapter, "fallback_policy", "FALLBACK_DISABLED"),
    })


@router.get("/providers/{provider_id}/models")
async def get_provider_models(
    provider_id: str,
    request: Request,
    authorization: Optional[str] = Header(None),
):
    """Retrieves models hosted by a specific provider without merging identities."""
    client_host = request.client.host if request.client else "127.0.0.1"
    openai_service.authenticate_request(authorization, client_host)
    from ai.providers.registry import provider_registry

    models = await provider_registry.get_provider_models(provider_id)
    return JSONResponse(content={"provider": provider_id, "models": models})
