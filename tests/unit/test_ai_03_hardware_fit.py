"""
Phase AI-03 Test Suite: Runtime Profiles & Hardware Fit Engine
Tests memory admission control, KV cache scaling, GPU offload layer partitioning, task capability gating, and concurrency.
"""

import pytest
from unittest.mock import patch

from ai.hardware.fit_engine import (
    FitStatusEnum,
    HardwareFitEngine,
    HardwareFitResult,
    OffloadStrategyEnum,
    RecommendationEnum,
)
from ai.hardware.fit_service import HardwareFitService
from ai.hardware.kv_cache import KVCacheEstimator
from ai.core.compatibility import HostCpuSpecs, HostGpuSpecs, HostRamSpecs
from ai.hardware.profiles import (
    RUNTIME_PROFILES,
    ConcurrencyPolicyEnum,
    RuntimeProfileName,
)
from ai.registry.models import (
    ModelCapabilityEnum,
    ModelFormatEnum,
    ModelManifest,
    ModelStatusEnum,
    ModelTaskTypeEnum,
)


@pytest.fixture
def mock_poc_hardware():
    """Returns detected hardware snapshot for the Windows RTX 4060 Laptop (8GB VRAM, 16GB RAM)."""
    cpu = HostCpuSpecs(architecture="AMD64", physical_cores=12, logical_cores=24, has_avx2=True, has_avx512=True)
    ram = HostRamSpecs(total_gb=16.0, available_gb=10.0, used_gb=6.0, percent_used=37.5, safe_ai_budget_gb=9.0)
    gpu = HostGpuSpecs(
        is_available=True,
        device_name="NVIDIA GeForce RTX 4060 Laptop GPU",
        total_vram_gb=8.0,
        free_vram_gb=7.0,
        driver_version="610.47",
        cuda_driver_supported=True,
    )
    return cpu, ram, gpu


@pytest.fixture
def sample_qwen_3b_manifest():
    return ModelManifest(
        model_id="qwen2.5-3b-instruct-q4_k_m",
        display_name="Qwen 2.5 3B Instruct Q4",
        file_path="./models/gguf/qwen2.5-3b.gguf",
        file_size_bytes=1932735280,  # ~1843 MB
        sha256_checksum="e" * 64,
        format=ModelFormatEnum.GGUF,
        quantization="Q4_K_M",
        architecture="qwen2.5-3b",
        parameter_count="3.09B",
        context_length=32768,
        recommended_context_length=4096,
        primary_task_type=ModelTaskTypeEnum.GENERATION,
        capabilities=[ModelCapabilityEnum.GENERATION, ModelCapabilityEnum.STRUCTURED_OUTPUT],
        estimated_vram_mb=1900,
        estimated_ram_mb=2200,
        status=ModelStatusEnum.ACTIVE_REGISTERED,
    )


@pytest.fixture
def sample_qwen_7b_manifest():
    return ModelManifest(
        model_id="qwen2.5-7b-instruct-q4_k_m",
        display_name="Qwen 2.5 7B Instruct Q4",
        file_path="./models/gguf/qwen2.5-7b.gguf",
        file_size_bytes=4600000000,  # ~4386 MB
        sha256_checksum="f" * 64,
        format=ModelFormatEnum.GGUF,
        quantization="Q4_K_M",
        architecture="qwen2.5-7b",
        parameter_count="7.61B",
        context_length=32768,
        recommended_context_length=4096,
        primary_task_type=ModelTaskTypeEnum.GENERATION,
        capabilities=[ModelCapabilityEnum.GENERATION, ModelCapabilityEnum.STRUCTURED_OUTPUT],
        estimated_vram_mb=4500,
        estimated_ram_mb=5000,
        status=ModelStatusEnum.ACTIVE_REGISTERED,
    )


# ==============================================================================
# 1. RUNTIME PROFILES & MEMORY FIT TESTS
# ==============================================================================

def test_runtime_profiles_catalog_validity():
    """Verifies all runtime profile policies adhere to boundary constraints."""
    for name, policy in RUNTIME_PROFILES.items():
        assert policy.name == name
        assert 0.0 <= policy.vram_budget_ratio <= 1.0
        assert 0.5 <= policy.ram_budget_ratio <= 1.0
        assert policy.vram_safety_headroom_mb >= 0
        assert policy.ram_safety_headroom_mb >= 512


def test_qwen_3b_fits_fully_on_8gb_vram(mock_poc_hardware, sample_qwen_3b_manifest):
    """Test: 3B model at 4K context fits comfortably in 8GB VRAM (Full GPU Offload)."""
    cpu, ram, gpu = mock_poc_hardware
    res = HardwareFitEngine.evaluate_fit(
        manifest=sample_qwen_3b_manifest,
        target_task=ModelTaskTypeEnum.GENERATION,
        gpu_info=gpu,
        ram_info=ram,
        cpu_info=cpu,
        context_length=4096,
        requested_profile=RuntimeProfileName.PROFILE_CONSTRAINED,
    )

    assert res.compatible is True
    assert res.status == FitStatusEnum.SAFE
    assert res.recommendation == RecommendationEnum.RECOMMENDED
    assert res.recommended_offload_strategy == OffloadStrategyEnum.FULL_GPU
    assert res.recommended_gpu_layers == 36
    assert res.estimated_peak_memory_mb < res.usable_vram_budget_mb


def test_context_increase_triggers_caution_or_recalculation(mock_poc_hardware, sample_qwen_7b_manifest):
    """Test: 7B model at 4K context vs 32K context demonstrates dynamic KV cache scaling."""
    cpu, ram, gpu = mock_poc_hardware

    # 1. At 4K Context: Fits in VRAM (~4.5GB weights + ~500MB KV + ~350MB overhead = ~5.35GB)
    res_4k = HardwareFitEngine.evaluate_fit(
        manifest=sample_qwen_7b_manifest,
        target_task=ModelTaskTypeEnum.GENERATION,
        gpu_info=gpu,
        ram_info=ram,
        cpu_info=cpu,
        context_length=4096,
        requested_profile=RuntimeProfileName.PROFILE_CONSTRAINED,
    )
    assert res_4k.compatible is True
    assert res_4k.status in [FitStatusEnum.SAFE, FitStatusEnum.CAUTION]

    # 2. At 32K Context: KV cache expands significantly (~4GB KV), exceeding 8GB usable VRAM budget -> Partial/CPU
    res_32k = HardwareFitEngine.evaluate_fit(
        manifest=sample_qwen_7b_manifest,
        target_task=ModelTaskTypeEnum.GENERATION,
        gpu_info=gpu,
        ram_info=ram,
        cpu_info=cpu,
        context_length=32768,
        requested_profile=RuntimeProfileName.PROFILE_CONSTRAINED,
    )
    assert res_32k.estimated_kv_cache_mb > res_4k.estimated_kv_cache_mb
    assert res_32k.estimated_peak_memory_mb > res_32k.usable_vram_budget_mb
    assert res_32k.status in [FitStatusEnum.CAUTION, FitStatusEnum.UNSAFE]


# ==============================================================================
# 2. TASK CAPABILITY & INCOMPATIBILITY GATES
# ==============================================================================

def test_task_capability_incompatibility_gate(mock_poc_hardware, sample_qwen_3b_manifest):
    """Test: Requesting EMBEDDING on a GENERATION-only model returns INCOMPATIBLE."""
    cpu, ram, gpu = mock_poc_hardware
    res = HardwareFitEngine.evaluate_fit(
        manifest=sample_qwen_3b_manifest,
        target_task=ModelTaskTypeEnum.EMBEDDING,  # Incompatible task!
        gpu_info=gpu,
        ram_info=ram,
        cpu_info=cpu,
    )

    assert res.compatible is False
    assert res.status == FitStatusEnum.INCOMPATIBLE
    assert res.recommendation == RecommendationEnum.INCOMPATIBLE
    assert any("does not declare capability" in r for r in res.reasons)


# ==============================================================================
# 3. MEMORY PRESSURE, PARTIAL OFFLOAD & CPU FALLBACK
# ==============================================================================

def test_active_vram_pressure_reduces_usable_budget(mock_poc_hardware, sample_qwen_3b_manifest):
    """Test: Active external VRAM pressure (e.g. 5GB used by 3D CAD) reduces usable budget."""
    cpu, ram, gpu = mock_poc_hardware
    res = HardwareFitEngine.evaluate_fit(
        manifest=sample_qwen_3b_manifest,
        target_task=ModelTaskTypeEnum.GENERATION,
        gpu_info=gpu,
        ram_info=ram,
        cpu_info=cpu,
        active_vram_pressure_mb=5000,  # 5GB consumed by other apps
    )

    assert any("Active external VRAM pressure" in w for w in res.warnings)


def test_cpu_only_profile_and_fallback(mock_poc_hardware, sample_qwen_3b_manifest):
    """Test: CPU-ONLY profile forces CPU execution in RAM regardless of GPU presence."""
    cpu, ram, gpu = mock_poc_hardware
    res = HardwareFitEngine.evaluate_fit(
        manifest=sample_qwen_3b_manifest,
        target_task=ModelTaskTypeEnum.GENERATION,
        gpu_info=gpu,
        ram_info=ram,
        cpu_info=cpu,
        requested_profile=RuntimeProfileName.CPU_ONLY,
    )

    assert res.recommended_offload_strategy == OffloadStrategyEnum.CPU_ONLY
    assert res.recommended_gpu_layers == 0
    assert res.usable_vram_budget_mb == 0


def test_gpu_unavailable_falls_back_to_ram(sample_qwen_3b_manifest):
    """Test: When GPU is completely absent, engine allocates in RAM safely."""
    cpu = HostCpuSpecs(architecture="AMD64", physical_cores=8, logical_cores=16)
    ram = HostRamSpecs(total_gb=32.0, available_gb=24.0, used_gb=8.0, percent_used=25.0, safe_ai_budget_gb=23.0)
    gpu = HostGpuSpecs(is_available=False)

    res = HardwareFitEngine.evaluate_fit(
        manifest=sample_qwen_3b_manifest,
        target_task=ModelTaskTypeEnum.GENERATION,
        gpu_info=gpu,
        ram_info=ram,
        cpu_info=cpu,
    )

    assert res.compatible is True
    assert res.recommended_offload_strategy == OffloadStrategyEnum.CPU_ONLY
    assert res.status == FitStatusEnum.SAFE


# ==============================================================================
# 4. CONCURRENCY & MULTI-MODEL ADMISSION CONTROL
# ==============================================================================

def test_concurrency_gate_enforces_sequential_on_constrained_profile(sample_qwen_3b_manifest, sample_qwen_7b_manifest):
    """Test: Requesting co-residency of two models on PROFILE-CONSTRAINED routes to SEQUENTIAL_SWAP."""
    with patch.object(HardwareFitService, "evaluate_model_fit") as mock_eval:
        mock_eval.return_value = HardwareFitResult(
            compatible=True,
            status=FitStatusEnum.SAFE,
            recommendation=RecommendationEnum.RECOMMENDED,
            usable_vram_budget_mb=5500,
            usable_ram_budget_mb=7000,
            estimated_model_weights_mb=2000,
            estimated_kv_cache_mb=400,
            estimated_runtime_overhead_mb=350,
            estimated_peak_memory_mb=2750,
            recommended_offload_strategy=OffloadStrategyEnum.FULL_GPU,
            recommended_gpu_layers=36,
            total_model_layers=36,
            recommended_context_length=4096,
            recommended_runtime_profile=RuntimeProfileName.PROFILE_CONSTRAINED,
            safety_headroom_mb=512,
        )

        res = HardwareFitService.evaluate_concurrency_fit(
            models_and_tasks=[
                (sample_qwen_3b_manifest, ModelTaskTypeEnum.GENERATION),
                (sample_qwen_7b_manifest, ModelTaskTypeEnum.GENERATION),
            ],
            requested_profile=RuntimeProfileName.PROFILE_CONSTRAINED,
        )

        assert res.is_concurrent_allowed is False
        assert res.concurrency_policy == ConcurrencyPolicyEnum.SEQUENTIAL
        assert res.recommended_action == "SEQUENTIAL_SWAP"


# ==============================================================================
# 5. KV CACHE ESTIMATOR TESTS
# ==============================================================================

def test_kv_cache_exact_analytical_calculation():
    """Verifies analytical calculation for Qwen2 3B architecture."""
    est = KVCacheEstimator.estimate_kv_cache(
        context_length=4096,
        architecture="qwen2-3b",
        batch_size=1,
    )
    assert est.is_exact_analytical is True
    assert est.estimated_kv_mb > 0
    assert est.insufficient_metadata is False


def test_kv_cache_heuristic_fallback_on_unknown_arch():
    """Verifies heuristic fallback when architecture metadata is unknown."""
    est = KVCacheEstimator.estimate_kv_cache(
        context_length=4096,
        architecture="unknown_exotic_arch_xyz",
        parameter_count=None,
    )
    assert est.is_exact_analytical is False
    assert est.insufficient_metadata is True
    assert est.estimated_kv_mb >= 32
