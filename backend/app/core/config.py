"""
Application Configuration Module
Enforces typed settings, dynamic environment resolution, and air-gap flags.
"""

from typing import List, Optional
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    # General Project Information
    PROJECT_NAME: str = "HERO Vehicle Cost & Plant OPEX Intelligence Platform"
    VERSION: str = "0.1.0-alpha"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Local OpenAI-Compatible API Settings (AI-14)
    OPENAI_API_AUTH_MODE: str = "trusted_local"  # "trusted_local", "api_key", "disabled"
    OPENAI_API_KEY: str = "hero-local-ai-key-secret"
    OPENAI_API_MAX_CONCURRENCY: int = 4

    # Air-Gap & Zero Telemetry Governance
    AIR_GAP_MODE: bool = True
    ENABLE_TELEMETRY: bool = False
    ALLOW_EXTERNAL_EGRESS: bool = False

    # Security & JWT Tokens
    SECRET_KEY: str = "hero-synthetic-demo-secret-key-change-in-production-airgap"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Database Configuration (PostgreSQL 16 + pgvector)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "hero_admin"
    POSTGRES_PASSWORD: str = "hero_secure_password"
    POSTGRES_DB: str = "hero_cost_intel"

    DATABASE_URL: Optional[str] = None
    DATABASE_URL_SYNC: Optional[str] = None

    @computed_field
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    def SQLALCHEMY_SYNC_DATABASE_URI(self) -> str:
        if self.DATABASE_URL_SYNC:
            return self.DATABASE_URL_SYNC
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@"
            f"{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Hardware Profiling & Local AI Settings
    HARDWARE_PROFILE_OVERRIDE: str = "AUTO"  # AUTO, TIER1_LOW, TIER2_MED, TIER3_HIGH, CPU_ONLY
    MAX_SAFE_RAM_PERCENT: int = 75
    LLAMA_NUM_THREADS: int = 6
    DEFAULT_REASONING_MODEL: str = "Qwen2.5-7B-Instruct-Q3_K_M.gguf"
    DEFAULT_EMBEDDING_MODEL: str = "Qwen3-Embedding-0.6B"
    DEFAULT_RERANKER_MODEL: str = "Qwen3-Reranker-0.6B"
    MODEL_REGISTRY_PATH: str = "./models"


settings = Settings()
