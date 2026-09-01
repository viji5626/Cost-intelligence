"""
Hardware Resource Profiler
Dynamically inspects host resources (CPU, RAM, GPU/VRAM) to select execution tiers.
"""

import platform
import psutil
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from ai.hardware.models import (
    CpuInfo,
    ExecutionMode,
    GpuInfo,
    HardwareProfile,
    HardwareResourceTier,
    RamInfo,
)
from backend.app.core.config import settings
from backend.app.core.logging import logger

if TYPE_CHECKING:
    from ai.core.compatibility import NativeCompatibilityReport


class HardwareProfiler:
    """Detects system hardware and allocates dynamic memory and model execution profiles."""

    @staticmethod
    def detect_cpu() -> CpuInfo:
        physical = psutil.cpu_count(logical=False) or 4
        logical = psutil.cpu_count(logical=True) or 8
        usage = psutil.cpu_percent(interval=None)

        # Thread recommendation: reserve headroom for web server & DB
        recommended = settings.LLAMA_NUM_THREADS
        if recommended <= 0 or recommended > logical:
            recommended = max(1, min(6, physical))

        return CpuInfo(
            architecture=platform.machine(),
            physical_cores=physical,
            logical_cores=logical,
            recommended_threads=recommended,
            cpu_percent_usage=usage,
        )

    @staticmethod
    def detect_ram() -> RamInfo:
        mem = psutil.virtual_memory()
        total_gb = round(mem.total / (1024**3), 2)
        avail_gb = round(mem.available / (1024**3), 2)
        used_gb = round(mem.used / (1024**3), 2)

        # Safety calculation: leave at least 1.0 GB safety margin
        safe_budget = max(0.5, round(avail_gb - 1.0, 2))

        return RamInfo(
            total_gb=total_gb,
            available_gb=avail_gb,
            used_gb=used_gb,
            percent_used=mem.percent,
            safe_ai_budget_gb=safe_budget,
        )

    @staticmethod
    def detect_gpu() -> GpuInfo:
        # Check for PyTorch / CUDA capability first
        try:
            import importlib
            torch = importlib.import_module("torch")

            if getattr(torch, "cuda", None) and torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                total_vram = round(
                    torch.cuda.get_device_properties(0).total_memory / (1024**3), 2
                )
                free_mem, _ = torch.cuda.mem_get_info(0)
                free_vram = round(free_mem / (1024**3), 2)
                return GpuInfo(
                    is_available=True,
                    device_name=name,
                    total_vram_gb=total_vram,
                    free_vram_gb=free_vram,
                    cuda_driver_version=torch.version.cuda,
                )
        except Exception:
            pass

        # Strategy 2: Direct nvidia-smi command-line probe for native driver inspection
        try:
            import shutil
            import subprocess

            smi_path = shutil.which("nvidia-smi")
            if smi_path:
                res = subprocess.run(
                    [smi_path, "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=3.0,
                    check=False,
                )
                if res.returncode == 0 and res.stdout.strip():
                    parts = [p.strip() for p in res.stdout.strip().split(",")]
                    if len(parts) >= 4:
                        name = parts[0]
                        total_vram = round(float(parts[1]) / 1024.0, 2)
                        free_vram = round(float(parts[2]) / 1024.0, 2)
                        driver = parts[3]
                        return GpuInfo(
                            is_available=True,
                            device_name=name,
                            total_vram_gb=total_vram,
                            free_vram_gb=free_vram,
                            cuda_driver_version=f"Driver {driver}",
                        )
        except Exception:
            pass

        # Fallback inspection if GPU not present or undetectable
        return GpuInfo(
            is_available=False,
            device_name=None,
            total_vram_gb=0.0,
            free_vram_gb=0.0,
            cuda_driver_version=None,
        )

    @classmethod
    def get_compatibility_report(cls) -> "NativeCompatibilityReport":
        from ai.core.compatibility import NativeCompatibilityGate
        return NativeCompatibilityGate.run_preflight_gate()

    @classmethod
    def get_profile(cls) -> HardwareProfile:
        cpu = cls.detect_cpu()
        ram = cls.detect_ram()
        gpu = cls.detect_gpu()

        override = settings.HARDWARE_PROFILE_OVERRIDE.upper()

        if override == "TIER1_LOW":
            tier = HardwareResourceTier.TIER1_LOW
            exec_mode = ExecutionMode.GPU_PARTIAL_OFFLOAD if gpu.is_available else ExecutionMode.CPU_FALLBACK
            context_win = 4096
            models = ["Qwen2.5-3B-Instruct-Q4_K_M.gguf", "Qwen2.5-7B-Instruct-Q3_K_M.gguf"]
        elif override == "TIER2_MED":
            tier = HardwareResourceTier.TIER2_MEDIUM
            exec_mode = ExecutionMode.GPU_FULL_OFFLOAD if gpu.is_available else ExecutionMode.CPU_FALLBACK
            context_win = 8192
            models = ["Qwen2.5-7B-Instruct-Q4_K_M.gguf", "Qwen3.5-9B-Instruct-Q4_K_M.gguf"]
        elif override == "TIER3_HIGH":
            tier = HardwareResourceTier.TIER3_HIGH
            exec_mode = ExecutionMode.GPU_FULL_OFFLOAD
            context_win = 16384
            models = ["Qwen2.5-14B-Instruct-Q4_K_M.gguf", "Qwen3.5-9B-Instruct-Q8_0.gguf"]
        elif override == "CPU_ONLY":
            tier = HardwareResourceTier.CPU_ONLY
            exec_mode = ExecutionMode.CPU_FALLBACK
            context_win = 2048
            models = ["Qwen2.5-3B-Instruct-Q4_K_M.gguf"]
        else:
            # AUTO Detection based on RAM and VRAM
            if gpu.is_available:
                if gpu.total_vram_gb >= 20.0 and ram.total_gb >= 48.0:
                    tier = HardwareResourceTier.TIER3_HIGH
                    exec_mode = ExecutionMode.GPU_FULL_OFFLOAD
                    context_win = 16384
                    models = ["Qwen2.5-14B-Instruct-Q4_K_M.gguf", "Qwen3.5-9B-Instruct-Q8_0.gguf"]
                elif gpu.total_vram_gb >= 12.0 and ram.total_gb >= 24.0:
                    tier = HardwareResourceTier.TIER2_MEDIUM
                    exec_mode = ExecutionMode.GPU_FULL_OFFLOAD
                    context_win = 8192
                    models = ["Qwen2.5-7B-Instruct-Q4_K_M.gguf", "Qwen3.5-9B-Instruct-Q4_K_M.gguf"]
                else:
                    # 8 GB VRAM / 16 GB RAM baseline (POC Laptop Profile)
                    tier = HardwareResourceTier.TIER1_LOW
                    exec_mode = ExecutionMode.GPU_PARTIAL_OFFLOAD
                    context_win = 4096
                    models = ["Qwen2.5-3B-Instruct-Q4_K_M.gguf", "Qwen2.5-7B-Instruct-Q3_K_M.gguf"]
            else:
                tier = HardwareResourceTier.CPU_ONLY
                exec_mode = ExecutionMode.CPU_FALLBACK
                context_win = 2048
                models = ["Qwen2.5-3B-Instruct-Q4_K_M.gguf"]

        profile = HardwareProfile(
            tier=tier,
            execution_mode=exec_mode,
            cpu=cpu,
            ram=ram,
            gpu=gpu,
            max_context_window=context_win,
            supported_models=models,
            supports_sequential_swapping=True,
            profile_timestamp=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(
            f"Hardware Profiler initialized: Tier={profile.tier.value}, "
            f"Mode={profile.execution_mode.value}, "
            f"RAM Budget={profile.ram.safe_ai_budget_gb}GB, "
            f"Context={profile.max_context_window}"
        )
        return profile
