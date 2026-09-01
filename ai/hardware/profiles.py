"""
Runtime Profile Policy & Resource Budget Definitions
Defines first-class hardware-agnostic runtime profiles for admission control, memory budgets, and concurrency.
"""

from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field


class RuntimeProfileName(str, Enum):
    AUTO = "AUTO"
    PROFILE_CONSTRAINED = "PROFILE-CONSTRAINED"    # 8GB VRAM / 16GB RAM (Sequential Swapping)
    PROFILE_BALANCED = "PROFILE-BALANCED"          # 12-16GB VRAM / 32GB RAM (Dual Resident)
    PROFILE_PERFORMANCE = "PROFILE-PERFORMANCE"    # 24GB VRAM / 64GB RAM (Fully Concurrent)
    PROFILE_ENTERPRISE = "PROFILE-ENTERPRISE"      # 48GB+ VRAM / 128GB+ RAM (High-Throughput Pool)
    CPU_ONLY = "CPU-ONLY"                          # Zero GPU acceleration


class ConcurrencyPolicyEnum(str, Enum):
    SEQUENTIAL = "SEQUENTIAL"                      # Strictly 1 resident model; swap on task switch
    DUAL_RESIDENT = "DUAL_RESIDENT"                # Generation + Embedding/Reranker co-resident
    FULL_CONCURRENT = "FULL_CONCURRENT"            # Multiple generation & retrieval workers in VRAM
    HIGH_THROUGHPUT_POOL = "HIGH_THROUGHPUT_POOL"  # Dynamic model worker pool with batching


class PreferredOffloadStrategy(str, Enum):
    FULL_GPU_ONLY = "FULL_GPU_ONLY"
    PARTIAL_GPU_ACCEPTABLE = "PARTIAL_GPU_ACCEPTABLE"
    CPU_ONLY = "CPU_ONLY"
    DYNAMIC_OPTIMAL = "DYNAMIC_OPTIMAL"


class RuntimeProfilePolicy(BaseModel):
    """Defines resource governance and execution policy for a hardware profile."""

    name: RuntimeProfileName
    display_name: str
    description: str
    vram_budget_ratio: float = Field(default=0.85, ge=0.0, le=0.95, description="Fraction of available VRAM usable for AI")
    ram_budget_ratio: float = Field(default=0.75, ge=0.5, le=0.90, description="Fraction of available RAM usable for AI")
    concurrency_policy: ConcurrencyPolicyEnum = ConcurrencyPolicyEnum.SEQUENTIAL
    preferred_offload: PreferredOffloadStrategy = PreferredOffloadStrategy.DYNAMIC_OPTIMAL
    vram_safety_headroom_mb: int = Field(default=512, ge=0, description="Fixed VRAM reserved for OS/display in MB")
    ram_safety_headroom_mb: int = Field(default=1024, ge=512, description="Fixed host RAM reserved for OS in MB")
    max_context_limit: int = Field(default=4096, ge=512, description="Maximum recommended context length")
    allow_cpu_fallback: bool = True
    max_concurrent_models: int = 1


# Canonical Profile Catalog
RUNTIME_PROFILES: Dict[RuntimeProfileName, RuntimeProfilePolicy] = {
    RuntimeProfileName.PROFILE_CONSTRAINED: RuntimeProfilePolicy(
        name=RuntimeProfileName.PROFILE_CONSTRAINED,
        display_name="Profile: Constrained (8GB VRAM / 16GB RAM)",
        description="Optimized for laptops and entry workstations. Enforces sequential swapping and partial/full offload.",
        vram_budget_ratio=0.85,
        ram_budget_ratio=0.75,
        concurrency_policy=ConcurrencyPolicyEnum.SEQUENTIAL,
        preferred_offload=PreferredOffloadStrategy.PARTIAL_GPU_ACCEPTABLE,
        vram_safety_headroom_mb=512,
        ram_safety_headroom_mb=1024,
        max_context_limit=4096,
        allow_cpu_fallback=True,
        max_concurrent_models=1,
    ),
    RuntimeProfileName.PROFILE_BALANCED: RuntimeProfilePolicy(
        name=RuntimeProfileName.PROFILE_BALANCED,
        display_name="Profile: Balanced (12-16GB VRAM / 32GB RAM)",
        description="Optimized for professional workstations. Permits dual co-resident models (e.g. SLM + Embedding).",
        vram_budget_ratio=0.88,
        ram_budget_ratio=0.80,
        concurrency_policy=ConcurrencyPolicyEnum.DUAL_RESIDENT,
        preferred_offload=PreferredOffloadStrategy.FULL_GPU_ONLY,
        vram_safety_headroom_mb=768,
        ram_safety_headroom_mb=2048,
        max_context_limit=8192,
        allow_cpu_fallback=True,
        max_concurrent_models=2,
    ),
    RuntimeProfileName.PROFILE_PERFORMANCE: RuntimeProfilePolicy(
        name=RuntimeProfileName.PROFILE_PERFORMANCE,
        display_name="Profile: Performance (24GB VRAM / 64GB RAM)",
        description="Optimized for high-end AI workstations. Fully concurrent SLM, Embeddings, and Rerankers.",
        vram_budget_ratio=0.90,
        ram_budget_ratio=0.85,
        concurrency_policy=ConcurrencyPolicyEnum.FULL_CONCURRENT,
        preferred_offload=PreferredOffloadStrategy.FULL_GPU_ONLY,
        vram_safety_headroom_mb=1024,
        ram_safety_headroom_mb=4096,
        max_context_limit=16384,
        allow_cpu_fallback=False,
        max_concurrent_models=3,
    ),
    RuntimeProfileName.PROFILE_ENTERPRISE: RuntimeProfilePolicy(
        name=RuntimeProfileName.PROFILE_ENTERPRISE,
        display_name="Profile: Enterprise Server (48GB+ VRAM / 128GB+ RAM)",
        description="Optimized for multi-GPU data center servers. Dynamic worker pooling and large context support.",
        vram_budget_ratio=0.92,
        ram_budget_ratio=0.88,
        concurrency_policy=ConcurrencyPolicyEnum.HIGH_THROUGHPUT_POOL,
        preferred_offload=PreferredOffloadStrategy.FULL_GPU_ONLY,
        vram_safety_headroom_mb=2048,
        ram_safety_headroom_mb=8192,
        max_context_limit=32768,
        allow_cpu_fallback=False,
        max_concurrent_models=6,
    ),
    RuntimeProfileName.CPU_ONLY: RuntimeProfilePolicy(
        name=RuntimeProfileName.CPU_ONLY,
        display_name="Profile: CPU Only",
        description="Zero GPU acceleration. Utilizes AVX2/AVX-512 SIMD execution on host RAM.",
        vram_budget_ratio=0.0,
        ram_budget_ratio=0.70,
        concurrency_policy=ConcurrencyPolicyEnum.SEQUENTIAL,
        preferred_offload=PreferredOffloadStrategy.CPU_ONLY,
        vram_safety_headroom_mb=0,
        ram_safety_headroom_mb=1536,
        allow_cpu_fallback=True,
        max_concurrent_models=1,
    ),
}


def get_runtime_profile(name: RuntimeProfileName) -> RuntimeProfilePolicy:
    """Retrieves runtime profile policy or falls back to PROFILE_CONSTRAINED."""
    return RUNTIME_PROFILES.get(name, RUNTIME_PROFILES[RuntimeProfileName.PROFILE_CONSTRAINED])
