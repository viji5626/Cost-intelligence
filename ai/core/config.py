"""
Local AI Runtime Configuration Module
Clean configuration boundaries for models, hardware budgets, providers, and local runtime policies.
"""

import os
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeProfileEnum(str, Enum):
    AUTO = "AUTO"
    PROFILE_CONSTRAINED = "PROFILE-CONSTRAINED"    # 8GB VRAM / 16GB RAM baseline (Sequential Swap)
    PROFILE_BALANCED = "PROFILE-BALANCED"          # 12-16GB VRAM / 32GB RAM (Dual Resident)
    PROFILE_PERFORMANCE = "PROFILE-PERFORMANCE"    # 24GB VRAM / 64GB RAM (Fully Concurrent)
    PROFILE_ENTERPRISE = "PROFILE-ENTERPRISE"      # 48GB+ VRAM / 128GB+ RAM (High-Throughput Pool)
    CPU_ONLY = "CPU-ONLY"                          # Zero GPU acceleration


class PrimaryRuntimeBackend(str, Enum):
    BUILTIN_GGUF = "BUILTIN_GGUF"
    MOCK_DETERMINISTIC = "MOCK_DETERMINISTIC"


class AIRuntimeConfig(BaseSettings):
    """Configuration settings for Local AI Runtime and decoupled task providers."""

    model_config = SettingsConfigDict(
        env_prefix="HERO_AI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # 1. Model Storage & Registry Paths (Offline Local Only)
    MODEL_STORAGE_PATH: str = Field(default="./models/gguf", description="Directory where GGUF model binaries reside")
    MANIFEST_STORAGE_PATH: str = Field(default="./models/registry.json", description="Registry manifest JSON path")
    QUARANTINE_STORAGE_PATH: str = Field(default="./models/quarantine", description="Directory for quarantined models")

    # 2. Runtime Profile & Hardware Budget Governance
    ACTIVE_RUNTIME_PROFILE: RuntimeProfileEnum = Field(
        default=RuntimeProfileEnum.AUTO,
        description="Active runtime profile controlling VRAM/RAM budgets and concurrency",
    )
    VRAM_SAFETY_MARGIN_PERCENT: float = Field(
        default=10.0,
        ge=5.0,
        le=30.0,
        description="Percentage of available VRAM reserved as unallocated safety headroom",
    )
    RAM_SAFETY_MARGIN_GB: float = Field(
        default=1.0,
        ge=0.5,
        le=4.0,
        description="Host system RAM reserved in GB to prevent OS kernel OOM swapping",
    )
    INFERENCE_THREAD_ALLOCATION: int = Field(
        default=6,
        ge=1,
        le=32,
        description="Number of CPU worker threads pinned for local inference (Zen 5 cores)",
    )

    # 3. Primary Built-In Runtime Engine
    PRIMARY_BACKEND: PrimaryRuntimeBackend = Field(
        default=PrimaryRuntimeBackend.BUILTIN_GGUF,
        description="Default native execution backend for the platform",
    )
    DEFAULT_CONTEXT_WINDOW: int = Field(
        default=4096,
        ge=512,
        le=32768,
        description="Default context window in tokens",
    )
    RESERVED_OUTPUT_TOKENS: int = Field(
        default=768,
        ge=128,
        le=4096,
        description="Tokens reserved exclusively for structured model completion output",
    )
    DEFAULT_TEMPERATURE: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Default sampling temperature (0.0 for deterministic audit)",
    )
    DEFAULT_SEED: int = Field(
        default=42,
        description="Default random seed for reproducible sampling",
    )

    # 4. Optional Local Provider Adapters
    ENABLE_OLLAMA_ADAPTER: bool = Field(default=False, description="Enable optional local Ollama adapter")
    OLLAMA_ENDPOINT: str = Field(default="http://127.0.0.1:11434", description="Local Ollama endpoint URL")

    ENABLE_LM_STUDIO_ADAPTER: bool = Field(default=False, description="Enable optional local LM Studio adapter")
    LM_STUDIO_ENDPOINT: str = Field(default="http://127.0.0.1:1234/v1", description="Local LM Studio endpoint URL")

    ENABLE_NVIDIA_NIM_ADAPTER: bool = Field(default=False, description="Enable optional local NVIDIA NIM adapter")
    NVIDIA_NIM_ENDPOINT: str = Field(default="http://127.0.0.1:8000/v1", description="Local NVIDIA NIM endpoint URL")

    # 5. Local OpenAI-Compatible API Gateway
    ENABLE_LOCAL_OPENAI_API: bool = Field(
        default=True,
        description="Expose local-only OpenAI-compatible router (/v1/chat/completions)",
    )
    LOCAL_API_HOST: str = Field(default="127.0.0.1", description="Host binding for local API (strictly localhost)")
    LOCAL_API_PORT: int = Field(default=8000, description="Port for local API router")
    LOCAL_API_ALLOWED_ORIGINS: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
        description="Explicit restricted CORS origins for local AI API",
    )

    # 6. Feature Flags & Safety Guardrails
    ENABLE_GBNF_GRAMMAR: bool = Field(default=True, description="Enforce GBNF logit-constrained structured sampling")
    ENABLE_MCP_TOOLS: bool = Field(default=True, description="Enable sandboxed domain tools / local MCP router")
    MCP_DRY_RUN_DEFAULT: bool = Field(default=False, description="Default dry-run mode for MCP tools")
    MAX_RETRIEVAL_ITERATIONS: int = Field(default=3, ge=1, le=5, description="Max recursive retrieval iterations")
    MAX_TOOL_CALLS_PER_TASK: int = Field(default=3, ge=1, le=10, description="Max tool iterations per task")
    TOOL_EXECUTION_TIMEOUT_SECONDS: float = Field(default=3.0, ge=0.5, le=10.0, description="Max timeout per tool call")

    # 7. Local-Only Telemetry & Diagnostics Logging
    ENABLE_LOCAL_AI_LOGGING: bool = Field(default=True, description="Record structured audit metrics for AI runs")
    IDLE_MODEL_UNLOAD_TIMEOUT_SECONDS: int = Field(
        default=900,
        ge=60,
        description="Time in seconds (15 min) after which an idle resident model is purged from VRAM",
    )

    @field_validator("LOCAL_API_HOST")
    @classmethod
    def validate_localhost_binding(cls, v: str) -> str:
        # Enforce air-gap localhost policy
        allowed_hosts = ["127.0.0.1", "localhost", "::1"]
        if v not in allowed_hosts and not v.startswith("127."):
            raise ValueError(f"Security violation: Local AI API host must bind to localhost (127.0.0.1), got '{v}'")
        return v


# Global singleton configuration instance
ai_settings = AIRuntimeConfig()
