"""
Main FastAPI Application Entry Point
"""

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.v1.endpoints import openai_compat
from backend.app.api.v1.router import api_router
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.core.logging import logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifecycle handler."""
    setup_logging(log_level="DEBUG" if settings.DEBUG else "INFO")
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Air-Gap Mode: {settings.AIR_GAP_MODE}, Telemetry: {settings.ENABLE_TELEMETRY}")
    await init_db()
    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Configure CORS for local enterprise development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_tracing_middleware(request: Request, call_next) -> Response:
    """Attaches request_id and measures API response latency."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.time()

    # Enforce air-gap zero egress guard
    if settings.AIR_GAP_MODE and request.headers.get("X-External-Fetch") == "true":
        return JSONResponse(
            status_code=403,
            content={"error": "AIR_GAP_EGRESS_BLOCKED", "message": "External network egress is prohibited."},
        )

    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    return response


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Formats all HTTPExceptions into standard OpenAI error envelopes."""
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": str(exc.detail),
                "type": "invalid_request_error" if exc.status_code < 500 else "api_error",
                "code": str(exc.status_code),
            }
        },
    )


# Mount API Router
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(openai_compat.router, prefix="/v1")


@app.get("/")
async def root_redirect():
    """Root redirect endpoint with basic platform status."""
    return {
        "platform": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": f"{settings.API_V1_STR}/docs",
        "air_gap_mode": settings.AIR_GAP_MODE,
        "status": "operational",
    }
