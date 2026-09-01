"""
Native AI Runtime Compatibility Gate & Preflight Diagnostic Engine
Inspects host hardware, Python C-ABI boundaries, CUDA driver readiness, and native runtime capabilities.
"""

import ctypes
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import psutil
from pydantic import BaseModel, Field


class CompatibilityStatus(str, Enum):
    OPTIMAL_GPU = "OPTIMAL_GPU"                          # GPU + CUDA ready for full/partial offload
    CAPABLE_GPU_RESTRICTED = "CAPABLE_GPU_RESTRICTED"    # GPU present, driver ready, memory constrained (8GB baseline)
    CPU_FALLBACK_CAPABLE = "CPU_FALLBACK_CAPABLE"        # GPU unavailable; AVX2/AVX-512 CPU execution supported
    INSUFFICIENT_HARDWARE = "INSUFFICIENT_HARDWARE"      # Insufficient RAM/CPU for local SLM execution


class NativeStrategy(str, Enum):
    DIRECT_DLL_GPU = "DIRECT_DLL_GPU"                    # Direct in-process C shared library with CUDA offload
    ISOLATED_WORKER_GPU = "ISOLATED_WORKER_GPU"          # Subprocess worker wrapper with CUDA offload
    CPU_SIMD_DIRECT = "CPU_SIMD_DIRECT"                  # Direct CPU execution with AVX2/AVX-512 acceleration
    DEGRADED_CPU = "DEGRADED_CPU"                        # Constrained minimal CPU execution (small context)


class HostCpuSpecs(BaseModel):
    architecture: str
    physical_cores: int
    logical_cores: int
    has_avx2: bool = True
    has_avx512: bool = False
    has_fma: bool = True
    recommended_threads: int = 6


class HostRamSpecs(BaseModel):
    total_gb: float
    available_gb: float
    used_gb: float
    percent_used: float
    safe_ai_budget_gb: float


class HostGpuSpecs(BaseModel):
    is_available: bool = False
    device_name: Optional[str] = None
    total_vram_gb: float = 0.0
    free_vram_gb: float = 0.0
    driver_version: Optional[str] = None
    cuda_driver_supported: bool = False


class NativeCompatibilityReport(BaseModel):
    """Auditable diagnostic report produced by NativeCompatibilityGate."""
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    host_os: str
    os_release: str
    python_version: str
    python_compiler: str
    cpu: HostCpuSpecs
    ram: HostRamSpecs
    gpu: HostGpuSpecs
    status: CompatibilityStatus
    recommended_strategy: NativeStrategy
    is_gguf_supported: bool
    is_cuda_ready: bool
    detected_hardware_tier: str
    warnings: List[str] = Field(default_factory=list)
    native_dlls_found: List[str] = Field(default_factory=list)


class NativeCompatibilityGate:
    """
    Automated preflight compatibility gate.
    Probes system resources, native dynamic libraries, and CUDA capabilities.
    """

    @classmethod
    def detect_cpu(cls) -> HostCpuSpecs:
        physical = psutil.cpu_count(logical=False) or 4
        logical = psutil.cpu_count(logical=True) or 8
        arch = platform.machine()

        # On x86_64 / AMD64 modern processors, AVX2 and FMA are standard (including Ryzen Zen 5)
        has_avx2 = arch in ["AMD64", "x86_64", "x86"]
        has_fma = has_avx2
        has_avx512 = False

        # Check for AVX-512 capability on Windows AMD64 if queryable
        try:
            if sys.platform == "win32" and has_avx2:
                # AMD Ryzen AI 9 HX 370 (Zen 5) has native AVX-512
                processor_name = platform.processor()
                if "Ryzen" in processor_name or "Zen" in processor_name or "Intel" in processor_name:
                    has_avx512 = True
        except Exception:
            pass

        # Recommended threads: 6 for Zen 5 performance cores (leaving headroom for API & DB)
        rec_threads = max(1, min(6, physical))

        return HostCpuSpecs(
            architecture=arch,
            physical_cores=physical,
            logical_cores=logical,
            has_avx2=has_avx2,
            has_avx512=has_avx512,
            has_fma=has_fma,
            recommended_threads=rec_threads,
        )

    @classmethod
    def detect_ram(cls) -> HostRamSpecs:
        mem = psutil.virtual_memory()
        total_gb = round(mem.total / (1024**3), 2)
        avail_gb = round(mem.available / (1024**3), 2)
        used_gb = round(mem.used / (1024**3), 2)
        # Safe AI Budget: Leave at least 1.0 GB headroom for OS
        safe_budget = max(0.5, round(avail_gb - 1.0, 2))

        return HostRamSpecs(
            total_gb=total_gb,
            available_gb=avail_gb,
            used_gb=used_gb,
            percent_used=mem.percent,
            safe_ai_budget_gb=safe_budget,
        )

    @classmethod
    def detect_gpu(cls) -> HostGpuSpecs:
        # Strategy 1: PyTorch CUDA probe (if installed & initialized)
        try:
            import importlib
            torch = importlib.import_module("torch")
            if getattr(torch, "cuda", None) and torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                total_vram = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
                free_mem, _ = torch.cuda.mem_get_info(0)
                free_vram = round(free_mem / (1024**3), 2)
                cuda_ver = getattr(torch.version, "cuda", "unknown") if hasattr(torch, "version") else "unknown"
                return HostGpuSpecs(
                    is_available=True,
                    device_name=name,
                    total_vram_gb=total_vram,
                    free_vram_gb=free_vram,
                    driver_version=str(cuda_ver),
                    cuda_driver_supported=True,
                )
        except Exception:
            pass

        # Strategy 2: User-space CUDA Driver API probe via ctypes (nvcuda.dll / libcuda.so)
        try:
            if sys.platform == "win32":
                nvcuda = ctypes.windll.nvcuda
            else:
                nvcuda = ctypes.CDLL("libcuda.so")

            if nvcuda and nvcuda.cuInit(0) == 0:
                count = ctypes.c_int()
                if nvcuda.cuDeviceGetCount(ctypes.byref(count)) == 0 and count.value > 0:
                    dev = ctypes.c_int(0)
                    nvcuda.cuDeviceGet(ctypes.byref(dev), 0)
                    name_buf = ctypes.create_string_buffer(256)
                    nvcuda.cuDeviceGetName(name_buf, 256, dev)
                    total_mem = ctypes.c_size_t()
                    nvcuda.cuDeviceTotalMem_v2(ctypes.byref(total_mem), dev)
                    total_gb = round(total_mem.value / (1024**3), 2)
                    return HostGpuSpecs(
                        is_available=True,
                        device_name=name_buf.value.decode("utf-8", errors="ignore"),
                        total_vram_gb=total_gb,
                        free_vram_gb=round(total_gb * 0.9, 2),  # Estimated initial free
                        driver_version="CUDA Driver API Active",
                        cuda_driver_supported=True,
                    )
        except Exception:
            pass

        # Strategy 3: nvidia-smi command-line probe
        try:
            smi_path = shutil.which("nvidia-smi") or (
                r"C:\WINDOWS\system32\nvidia-smi.EXE" if sys.platform == "win32" and os.path.exists(r"C:\WINDOWS\system32\nvidia-smi.EXE") else None
            )
            if smi_path:
                res = subprocess.run(
                    [smi_path, "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader,nounits"],
                    capture_output=True,
                    text=True,
                    timeout=3.0,
                    check=False,
                )
                if res.returncode == 0 and res.stdout.strip() and "NVIDIA-SMI has failed" not in res.stdout:
                    parts = [p.strip() for p in res.stdout.strip().split(",")]
                    if len(parts) >= 4:
                        name = parts[0]
                        total_vram = round(float(parts[1]) / 1024.0, 2)
                        free_vram = round(float(parts[2]) / 1024.0, 2)
                        driver = parts[3]
                        return HostGpuSpecs(
                            is_available=True,
                            device_name=name,
                            total_vram_gb=total_vram,
                            free_vram_gb=free_vram,
                            driver_version=driver,
                            cuda_driver_supported=True,
                        )
        except Exception:
            pass

        # Strategy 4: Windows WMI VideoController probe (detects integrated/discrete graphics adapter)
        if sys.platform == "win32":
            try:
                ps_cmd = "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM, DriverVersion | ConvertTo-Json"
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", ps_cmd],
                    capture_output=True,
                    text=True,
                    timeout=3.0,
                    check=False,
                )
                if res.returncode == 0 and res.stdout.strip():
                    import json
                    data = json.loads(res.stdout.strip())
                    if isinstance(data, list):
                        data = data[0] if data else {}
                    name = data.get("Name")
                    adapter_ram = data.get("AdapterRAM") or 0
                    ram_gb = round(float(adapter_ram) / (1024**3), 2)
                    driver = data.get("DriverVersion", "Unknown")
                    if name:
                        is_nvidia = "NVIDIA" in name.upper() or "GEFORCE" in name.upper() or "RTX" in name.upper()
                        return HostGpuSpecs(
                            is_available=is_nvidia,
                            device_name=name,
                            total_vram_gb=ram_gb if ram_gb > 0 else (8.0 if is_nvidia else 0.5),
                            free_vram_gb=round((ram_gb if ram_gb > 0 else (8.0 if is_nvidia else 0.5)) * 0.85, 2),
                            driver_version=str(driver),
                            cuda_driver_supported=is_nvidia,
                        )
            except Exception:
                pass

        # Fallback: Zero GPU detected
        return HostGpuSpecs(
            is_available=False,
            device_name=None,
            total_vram_gb=0.0,
            free_vram_gb=0.0,
            driver_version=None,
            cuda_driver_supported=False,
        )

    @classmethod
    def probe_native_dlls(cls) -> List[str]:
        """Probes for local GGUF / llama C-shared libraries in search paths."""
        found_dlls: List[str] = []
        candidate_names = ["libllama.dll", "llama.dll", "ggml.dll", "libggml.dll"]
        search_paths = [
            ".",
            "./runtime/bin",
            "./runtime/lib",
            os.path.join(sys.prefix, "Library", "bin"),
            os.path.join(sys.prefix, "Lib", "site-packages", "llama_cpp", "lib"),
        ]

        for p in search_paths:
            if os.path.isdir(p):
                for fname in candidate_names:
                    full_path = os.path.join(p, fname)
                    if os.path.isfile(full_path):
                        found_dlls.append(os.path.abspath(full_path))

        return found_dlls

    @classmethod
    def run_preflight_gate(cls) -> NativeCompatibilityReport:
        """
        Executes full preflight compatibility audit and produces a certified report.
        """
        cpu = cls.detect_cpu()
        ram = cls.detect_ram()
        gpu = cls.detect_gpu()
        dlls = cls.probe_native_dlls()
        warnings: List[str] = []

        # Determine Hardware Tier
        if gpu.is_available and gpu.total_vram_gb >= 20.0 and ram.total_gb >= 48.0:
            tier = "ENTERPRISE_SERVER_24GB+"
        elif gpu.is_available and gpu.total_vram_gb >= 11.0 and ram.total_gb >= 24.0:
            tier = "WORKSTATION_12GB+"
        elif gpu.is_available and gpu.total_vram_gb >= 6.0:
            tier = "POC_LAPTOP_8GB"
        else:
            tier = "CPU_ONLY"

        # Python Version Audit (e.g. Python 3.14 considerations)
        py_ver_tuple = sys.version_info
        py_ver_str = f"{py_ver_tuple.major}.{py_ver_tuple.minor}.{py_ver_tuple.micro}"
        if py_ver_tuple >= (3, 14):
            warnings.append(
                f"Host Python is {py_ver_str} (Python 3.14+). Native pre-built C-extension wheels may require "
                f"dual compatibility via direct CTypes DLL binding or isolated worker subprocess."
            )

        # Assess Strategy and Status
        if ram.total_gb < 6.0:
            status = CompatibilityStatus.INSUFFICIENT_HARDWARE
            strategy = NativeStrategy.DEGRADED_CPU
            warnings.append(f"Insufficient RAM ({ram.total_gb} GB). Minimum safe RAM for local SLM is 8.0 GB.")
            is_gguf = False
            is_cuda = False
        elif gpu.is_available and gpu.cuda_driver_supported:
            if gpu.total_vram_gb >= 12.0:
                status = CompatibilityStatus.OPTIMAL_GPU
                strategy = NativeStrategy.DIRECT_DLL_GPU
            else:
                status = CompatibilityStatus.CAPABLE_GPU_RESTRICTED
                strategy = NativeStrategy.DIRECT_DLL_GPU
                warnings.append(
                    f"GPU has {gpu.total_vram_gb} GB VRAM ({gpu.free_vram_gb} GB free). "
                    f"Sequential model swapping and partial/full offload policy enforced."
                )
            is_gguf = True
            is_cuda = True
        elif cpu.has_avx2:
            status = CompatibilityStatus.CPU_FALLBACK_CAPABLE
            strategy = NativeStrategy.CPU_SIMD_DIRECT
            warnings.append("No CUDA GPU detected or available. Native GGUF will execute via CPU SIMD (AVX2/AVX-512).")
            is_gguf = True
            is_cuda = False
        else:
            status = CompatibilityStatus.INSUFFICIENT_HARDWARE
            strategy = NativeStrategy.DEGRADED_CPU
            warnings.append("CPU lacks AVX2 instruction set. Execution will suffer severe latency degradation.")
            is_gguf = False
            is_cuda = False

        report = NativeCompatibilityReport(
            host_os=f"{platform.system()} {platform.release()}",
            os_release=platform.version(),
            python_version=py_ver_str,
            python_compiler=platform.python_compiler(),
            cpu=cpu,
            ram=ram,
            gpu=gpu,
            status=status,
            recommended_strategy=strategy,
            is_gguf_supported=is_gguf,
            is_cuda_ready=is_cuda,
            detected_hardware_tier=tier,
            warnings=warnings,
            native_dlls_found=dlls,
        )

        return report
