"""
Hardware Profiling and Resource Tier Data Models
"""

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class ExecutionMode(str, Enum):
    GPU_FULL_OFFLOAD = "GPU_FULL_OFFLOAD"
    GPU_PARTIAL_OFFLOAD = "GPU_PARTIAL_OFFLOAD"
    CPU_FALLBACK = "CPU_FALLBACK"
    DEGRADED_MODE = "DEGRADED_MODE"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"


class HardwareResourceTier(str, Enum):
    TIER1_LOW = "TIER1_LOW"        # 16GB RAM / 8GB VRAM (POC Laptop baseline)
    TIER2_MEDIUM = "TIER2_MEDIUM"  # 32GB RAM / 16GB VRAM (Workstation)
    TIER3_HIGH = "TIER3_HIGH"      # 64GB+ RAM / 24GB+ VRAM (Enterprise Server)
    CPU_ONLY = "CPU_ONLY"          # Zero GPU available


class CpuInfo(BaseModel):
    architecture: str
    physical_cores: int
    logical_cores: int
    recommended_threads: int
    cpu_percent_usage: float


class RamInfo(BaseModel):
    total_gb: float
    available_gb: float
    used_gb: float
    percent_used: float
    safe_ai_budget_gb: float


class GpuInfo(BaseModel):
    is_available: bool = False
    device_name: Optional[str] = None
    total_vram_gb: float = 0.0
    free_vram_gb: float = 0.0
    cuda_driver_version: Optional[str] = None


class HardwareProfile(BaseModel):
    tier: HardwareResourceTier
    execution_mode: ExecutionMode
    cpu: CpuInfo
    ram: RamInfo
    gpu: GpuInfo
    max_context_window: int = 4096
    supported_models: List[str] = Field(default_factory=list)
    supports_sequential_swapping: bool = True
    profile_timestamp: str
