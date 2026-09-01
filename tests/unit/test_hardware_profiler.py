"""
Unit Tests for Dynamic Hardware Resource Profiler
"""

from ai.hardware.models import HardwareResourceTier, ExecutionMode
from ai.hardware.profiler import HardwareProfiler


def test_hardware_profiler_cpu_detection():
    cpu = HardwareProfiler.detect_cpu()
    assert cpu.physical_cores >= 1
    assert cpu.logical_cores >= 1
    assert cpu.recommended_threads >= 1


def test_hardware_profiler_ram_detection():
    ram = HardwareProfiler.detect_ram()
    assert ram.total_gb > 0
    assert ram.available_gb > 0
    assert ram.safe_ai_budget_gb > 0


def test_hardware_profiler_get_profile():
    profile = HardwareProfiler.get_profile()
    assert profile.tier in [
        HardwareResourceTier.TIER1_LOW,
        HardwareResourceTier.TIER2_MEDIUM,
        HardwareResourceTier.TIER3_HIGH,
        HardwareResourceTier.CPU_ONLY,
    ]
    assert profile.execution_mode in [
        ExecutionMode.GPU_FULL_OFFLOAD,
        ExecutionMode.GPU_PARTIAL_OFFLOAD,
        ExecutionMode.CPU_FALLBACK,
        ExecutionMode.DEGRADED_MODE,
    ]
    assert len(profile.supported_models) > 0
    assert profile.max_context_window in [2048, 4096, 8192, 16384]
