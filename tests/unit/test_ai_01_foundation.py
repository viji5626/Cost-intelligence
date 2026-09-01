"""
Phase AI-01 Test Suite: Runtime Foundation & Native Compatibility Gate
Tests configuration boundaries, native hardware inspection, compatibility gating, and failure modes.
"""

import pytest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from ai.core.config import (
    AIRuntimeConfig,
    PrimaryRuntimeBackend,
    RuntimeProfileEnum,
    ai_settings,
)
from ai.core.contracts import (
    AIExecutionEnvelope,
    EmbeddingEngineContract,
    InferenceEngineContract,
    LifecycleManagerContract,
    ModelFormatEnum,
    ModelManifestData,
    ModelProvenance,
    ModelStatusEnum,
    RerankerEngineContract,
    TaskType,
    ToolRegistryContract,
    VisionOCREngineContract,
)
from ai.core.compatibility import (
    CompatibilityStatus,
    HostCpuSpecs,
    HostGpuSpecs,
    HostRamSpecs,
    NativeCompatibilityGate,
    NativeCompatibilityReport,
    NativeStrategy,
)
from ai.hardware.profiler import HardwareProfiler


# ==============================================================================
# 1. AI RUNTIME CONFIGURATION TESTS
# ==============================================================================

def test_ai_config_defaults():
    """Verifies default AI runtime configuration values adhere to air-gap and safety policy."""
    cfg = AIRuntimeConfig()
    assert cfg.PRIMARY_BACKEND == PrimaryRuntimeBackend.BUILTIN_GGUF
    assert cfg.ACTIVE_RUNTIME_PROFILE == RuntimeProfileEnum.AUTO
    assert cfg.VRAM_SAFETY_MARGIN_PERCENT == 10.0
    assert cfg.RAM_SAFETY_MARGIN_GB == 1.0
    assert cfg.INFERENCE_THREAD_ALLOCATION == 6
    assert cfg.DEFAULT_CONTEXT_WINDOW == 4096
    assert cfg.RESERVED_OUTPUT_TOKENS == 768
    assert cfg.DEFAULT_TEMPERATURE == 0.0
    assert cfg.DEFAULT_SEED == 42
    assert cfg.ENABLE_GBNF_GRAMMAR is True
    assert cfg.ENABLE_MCP_TOOLS is True
    assert cfg.LOCAL_API_HOST == "127.0.0.1"


def test_ai_config_localhost_security_constraint():
    """Verifies that binding local AI API to external non-localhost IP raises validation error."""
    with pytest.raises(ValidationError):
        AIRuntimeConfig(LOCAL_API_HOST="192.168.1.50")

    with pytest.raises(ValidationError):
        AIRuntimeConfig(LOCAL_API_HOST="0.0.0.0")

    # Valid localhost bindings
    valid_cfg_1 = AIRuntimeConfig(LOCAL_API_HOST="localhost")
    assert valid_cfg_1.LOCAL_API_HOST == "localhost"

    valid_cfg_2 = AIRuntimeConfig(LOCAL_API_HOST="127.0.0.1")
    assert valid_cfg_2.LOCAL_API_HOST == "127.0.0.1"


def test_ai_config_bounds_enforcement():
    """Verifies bounds on safety margins, timeouts, and retrieval iterations."""
    with pytest.raises(ValidationError):
        AIRuntimeConfig(VRAM_SAFETY_MARGIN_PERCENT=1.0)  # Min is 5.0%

    with pytest.raises(ValidationError):
        AIRuntimeConfig(MAX_RETRIEVAL_ITERATIONS=10)  # Max is 5


# ==============================================================================
# 2. CONTRACTS & PROVENANCE ENVELOPE TESTS
# ==============================================================================

def test_model_provenance_and_execution_envelope():
    """Verifies AIExecutionEnvelope computes a valid SHA-256 audit hash."""
    provenance = ModelProvenance(
        model_id="qwen2.5-3b-instruct-q4",
        model_version="1.0.0",
        model_file_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        quantization="Q4_K_M",
        runtime_engine="BUILTIN_GGUF",
        runtime_profile="PROFILE-CONSTRAINED",
        context_length=4096,
        temperature=0.0,
        seed=42,
    )

    envelope = AIExecutionEnvelope[dict](
        task_id="task-test-001",
        task_type=TaskType.STRUCTURED_EXTRACTION,
        status="SUCCESS",
        result={"part_number": "53100-DEMO-001", "decision": "POTENTIAL_OPPORTUNITY"},
        raw_content='{"part_number": "53100-DEMO-001"}',
        grounding_score=0.92,
        provenance=provenance,
    )

    assert envelope.audit_hash != ""
    assert len(envelope.audit_hash) == 64
    assert envelope.status == "SUCCESS"
    assert envelope.result["part_number"] == "53100-DEMO-001"


def test_model_manifest_quarantine_default():
    """Verifies newly initialized model manifest starts in QUARANTINED state."""
    manifest = ModelManifestData(
        model_id="test-model-001",
        display_name="Test Model GGUF",
        file_path="./models/gguf/test.gguf",
        file_size_bytes=1000000,
        sha256_checksum="abc123hash",
        parameter_count="3B",
    )
    assert manifest.status == ModelStatusEnum.QUARANTINED
    assert manifest.format == ModelFormatEnum.GGUF
    assert manifest.quantization == "Q4_K_M"


# ==============================================================================
# 3. LIVE NATIVE COMPATIBILITY GATE TESTS
# ==============================================================================

def test_live_native_compatibility_gate():
    """Tests live preflight compatibility gate against the actual host machine."""
    report = NativeCompatibilityGate.run_preflight_gate()

    assert isinstance(report, NativeCompatibilityReport)
    assert report.cpu.physical_cores >= 1
    assert report.cpu.logical_cores >= 1
    assert report.ram.total_gb > 0.0
    assert report.status in [
        CompatibilityStatus.OPTIMAL_GPU,
        CompatibilityStatus.CAPABLE_GPU_RESTRICTED,
        CompatibilityStatus.CPU_FALLBACK_CAPABLE,
    ]
    assert report.recommended_strategy in [
        NativeStrategy.DIRECT_DLL_GPU,
        NativeStrategy.CPU_SIMD_DIRECT,
    ]
    assert report.is_gguf_supported is True


def test_hardware_profiler_compatibility_report_integration():
    """Verifies HardwareProfiler.get_compatibility_report() returns a valid certified report."""
    report = HardwareProfiler.get_compatibility_report()
    assert report is not None
    assert report.cpu.physical_cores >= 1
    assert report.ram.available_gb > 0.0


# ==============================================================================
# 4. FAILURE-INJECTION & SIMULATION TESTS
# ==============================================================================

def test_simulation_insufficient_ram():
    """Failure test: Simulates host with only 4 GB RAM -> rejects with INSUFFICIENT_HARDWARE."""
    mock_cpu = HostCpuSpecs(architecture="AMD64", physical_cores=4, logical_cores=8)
    mock_ram = HostRamSpecs(total_gb=4.0, available_gb=1.5, used_gb=2.5, percent_used=62.5, safe_ai_budget_gb=0.5)
    mock_gpu = HostGpuSpecs(is_available=False)

    with patch.object(NativeCompatibilityGate, "detect_cpu", return_value=mock_cpu), \
         patch.object(NativeCompatibilityGate, "detect_ram", return_value=mock_ram), \
         patch.object(NativeCompatibilityGate, "detect_gpu", return_value=mock_gpu):
        report = NativeCompatibilityGate.run_preflight_gate()

        assert report.status == CompatibilityStatus.INSUFFICIENT_HARDWARE
        assert report.recommended_strategy == NativeStrategy.DEGRADED_CPU
        assert report.is_gguf_supported is False
        assert any("Insufficient RAM" in w for w in report.warnings)


def test_simulation_constrained_8gb_gpu():
    """Test: Simulates 8 GB VRAM laptop host -> returns CAPABLE_GPU_RESTRICTED with sequential swap."""
    mock_cpu = HostCpuSpecs(architecture="AMD64", physical_cores=12, logical_cores=24)
    mock_ram = HostRamSpecs(total_gb=16.0, available_gb=10.0, used_gb=6.0, percent_used=37.5, safe_ai_budget_gb=9.0)
    mock_gpu = HostGpuSpecs(
        is_available=True,
        device_name="NVIDIA GeForce RTX 4060 Laptop GPU",
        total_vram_gb=8.0,
        free_vram_gb=6.5,
        driver_version="610.47",
        cuda_driver_supported=True,
    )

    with patch.object(NativeCompatibilityGate, "detect_cpu", return_value=mock_cpu), \
         patch.object(NativeCompatibilityGate, "detect_ram", return_value=mock_ram), \
         patch.object(NativeCompatibilityGate, "detect_gpu", return_value=mock_gpu):
        report = NativeCompatibilityGate.run_preflight_gate()

        assert report.status == CompatibilityStatus.CAPABLE_GPU_RESTRICTED
        assert report.recommended_strategy == NativeStrategy.DIRECT_DLL_GPU
        assert report.detected_hardware_tier == "POC_LAPTOP_8GB"
        assert report.is_cuda_ready is True
        assert report.is_gguf_supported is True
        assert any("Sequential model swapping" in w for w in report.warnings)


def test_simulation_enterprise_24gb_server():
    """Test: Simulates 24 GB VRAM workstation/server host -> returns OPTIMAL_GPU."""
    mock_cpu = HostCpuSpecs(architecture="AMD64", physical_cores=16, logical_cores=32)
    mock_ram = HostRamSpecs(total_gb=64.0, available_gb=48.0, used_gb=16.0, percent_used=25.0, safe_ai_budget_gb=47.0)
    mock_gpu = HostGpuSpecs(
        is_available=True,
        device_name="NVIDIA RTX A5000",
        total_vram_gb=24.0,
        free_vram_gb=22.0,
        driver_version="550.54",
        cuda_driver_supported=True,
    )

    with patch.object(NativeCompatibilityGate, "detect_cpu", return_value=mock_cpu), \
         patch.object(NativeCompatibilityGate, "detect_ram", return_value=mock_ram), \
         patch.object(NativeCompatibilityGate, "detect_gpu", return_value=mock_gpu):
        report = NativeCompatibilityGate.run_preflight_gate()

        assert report.status == CompatibilityStatus.OPTIMAL_GPU
        assert report.recommended_strategy == NativeStrategy.DIRECT_DLL_GPU
        assert report.detected_hardware_tier == "ENTERPRISE_SERVER_24GB+"
        assert report.is_cuda_ready is True


def test_simulation_cpu_lacking_avx2():
    """Failure test: Simulates legacy CPU lacking AVX2 -> returns INSUFFICIENT_HARDWARE."""
    mock_cpu = HostCpuSpecs(architecture="x86", physical_cores=2, logical_cores=2, has_avx2=False)
    mock_ram = HostRamSpecs(total_gb=16.0, available_gb=10.0, used_gb=6.0, percent_used=37.5, safe_ai_budget_gb=9.0)
    mock_gpu = HostGpuSpecs(is_available=False)

    with patch.object(NativeCompatibilityGate, "detect_cpu", return_value=mock_cpu), \
         patch.object(NativeCompatibilityGate, "detect_ram", return_value=mock_ram), \
         patch.object(NativeCompatibilityGate, "detect_gpu", return_value=mock_gpu):
        report = NativeCompatibilityGate.run_preflight_gate()

        assert report.status == CompatibilityStatus.INSUFFICIENT_HARDWARE
        assert report.is_gguf_supported is False
        assert any("CPU lacks AVX2" in w for w in report.warnings)
