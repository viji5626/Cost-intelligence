"""Unit Tests for Phase AI-18: Performance & Hardware Benchmarking Suite

Verifies:
- Hardware and environment baseline capture with human-readable OS
- BM-1: Hardware Fit predictions vs physical observations
- BM-2: Native inference latency, TTFT, throughput, and source recording
- BM-3: Retrieval scaling over 10,000+ synthetic documents and cross-encoder
- BM-4: Model lifecycle memory retention tracking (NO MATERIAL RETAINED VRAM OBSERVED)
- BM-5: Digital PDF text stream extraction vs raster OCR availability probe
- BM-6: GBNF grammar compilation and schema validation overhead
- BM-7: Local OpenAI API concurrency execution (Cold vs Warm)
- Failure mode diagnostics (oversized model admission denial)
- AI-04 native GGUF evidence reconciliation table
- Markdown report formatting and JSON report serialization
"""

import pytest
from ai.benchmark.benchmark_suite import BenchmarkSuite
from ai.benchmark.benchmark_runner import BenchmarkReportFormatter
from ai.benchmark.models import (
    BenchmarkCategoryEnum,
    BenchmarkClassificationEnum,
    ComprehensiveBenchmarkReport,
    HardwareEnvironmentBaseline,
    SingleBenchmarkMeasurement,
    StatisticalMetric,
)


@pytest.fixture
def suite():
    return BenchmarkSuite()


def test_01_hardware_baseline_capture(suite: BenchmarkSuite):
    """Test: Hardware environment baseline captures valid system specs and human-readable OS."""
    hw = suite.capture_hardware_baseline()
    assert "Windows" in hw.os_name
    assert hw.os_build != ""
    assert hw.python_version != ""
    assert hw.cpu_physical_cores > 0
    assert hw.ram_total_gb > 0.0
    assert hw.vram_total_mb > 0.0


def test_02_bm1_hardware_fit_predictions(suite: BenchmarkSuite):
    """Test: BM-1 compares memory predictions against physical observations across context windows."""
    models = suite.discover_eligible_models()
    assert len(models) > 0

    measurements = suite.run_bm1_hardware_fit(models)
    assert len(measurements) >= 5  # 5 context windows

    for m in measurements:
        assert m.category == BenchmarkCategoryEnum.BM1_HARDWARE_FIT
        assert BenchmarkClassificationEnum.REAL_HARDWARE in m.classifications
        assert m.metric_value is not None and m.metric_value >= 0.0
        assert "predicted_kv_cache_mb" in m.telemetry
        assert m.measurement_source == "nvidia-smi / HardwareProfiler"
        assert "provider" in m.runtime_identity


@pytest.mark.asyncio
async def test_03_bm2_native_inference(suite: BenchmarkSuite):
    """Test: BM-2 measures cold load, TTFT, throughput, and records measurement source."""
    models = suite.discover_eligible_models()
    measurements = await suite.run_bm2_native_inference(models)

    assert len(measurements) >= 3  # Cold load, TTFT, Throughput
    cat_names = [m.benchmark_name for m in measurements]
    assert any("Cold_Load" in n for n in cat_names)
    assert any("TTFT" in n for n in cat_names)
    assert any("Throughput" in n for n in cat_names)

    for m in measurements:
        assert m.measurement_source != ""
        assert "model_id" in m.runtime_identity


def test_04_bm3_retrieval_scale_10k(suite: BenchmarkSuite):
    """Test: BM-3 scales multi-channel retrieval across 10,000 synthetic records."""
    measurements = suite.run_bm3_retrieval_scale()

    assert len(measurements) >= 3
    for m in measurements:
        assert BenchmarkClassificationEnum.SYNTHETIC_DATA in m.classifications
        assert BenchmarkClassificationEnum.REAL_LOCAL_RUNTIME in m.classifications
        assert m.metric_value is not None and m.metric_value >= 0.0


@pytest.mark.asyncio
async def test_05_bm4_model_lifecycle_swapping(suite: BenchmarkSuite):
    """Test: BM-4 executes repeated load/unload swap cycles and checks memory stability."""
    models = suite.discover_eligible_models()
    measurements = await suite.run_bm4_model_lifecycle(models)

    assert len(measurements) >= 2
    unload_m = next(m for m in measurements if "Unload" in m.benchmark_name)
    assert "NO MATERIAL RETAINED VRAM OBSERVED" in unload_m.notes
    assert unload_m.measurement_source == "nvidia-smi / psutil"


@pytest.mark.asyncio
async def test_06_bm5_digital_pdf_vs_raster_ocr(suite: BenchmarkSuite):
    """Test: BM-5 separates digital PDF text extraction from raster OCR availability probe."""
    measurements = await suite.run_bm5_ocr_extraction()

    assert len(measurements) >= 2
    names = [m.benchmark_name for m in measurements]
    assert any("Digital_PDF" in n for n in names)
    assert any("Raster_Image_OCR" in n for n in names)

    raster_m = next(m for m in measurements if "Raster_Image_OCR" in m.benchmark_name)
    assert raster_m.status in ["SUCCESS", "NOT_AVAILABLE"]


def test_07_bm6_gbnf_compilation_and_validation(suite: BenchmarkSuite):
    """Test: BM-6 benchmarks GBNF grammar generation and Pydantic validation."""
    measurements = suite.run_bm6_gbnf_validation()

    assert len(measurements) >= 2
    gbnf_m = next(m for m in measurements if "GBNF" in m.benchmark_name)
    assert gbnf_m.metric_value is not None and gbnf_m.metric_value >= 0.0


@pytest.mark.asyncio
async def test_08_bm7_local_api_concurrency_cold_and_warm(suite: BenchmarkSuite):
    """Test: BM-7 executes cold first request and warm 1, 2, 4 concurrent requests."""
    measurements = await suite.run_bm7_api_concurrency()

    assert len(measurements) == 4  # 1 cold + 3 warm
    cold_m = next(m for m in measurements if "Cold" in m.benchmark_name)
    assert cold_m.status == "EXECUTED"

    warm_m = [m for m in measurements if "Warm" in m.benchmark_name]
    assert len(warm_m) == 3
    for m in warm_m:
        assert m.status == "EXECUTED"


def test_09_failure_modes_oversized_model(suite: BenchmarkSuite):
    """Test: Failure mode diagnostics verify deterministic admission denial of oversized models."""
    measurements = suite.run_failure_mode_measurements()

    assert len(measurements) >= 1
    assert measurements[0].status == "REJECTED"
    assert BenchmarkClassificationEnum.SIMULATED in measurements[0].classifications


def test_10_ai04_reconciliation_and_markdown_report(suite: BenchmarkSuite):
    """Test: AI-04 native evidence reconciliation and Markdown report generator."""
    reconciliation = suite.get_ai04_reconciliation_table()
    assert len(reconciliation) == 5

    hw = suite.capture_hardware_baseline()
    report = ComprehensiveBenchmarkReport(
        report_id="rep-test-01",
        hardware_baseline=hw,
        measurements=[
            SingleBenchmarkMeasurement(
                benchmark_name="Test_Metric",
                category=BenchmarkCategoryEnum.BM1_HARDWARE_FIT,
                classifications=[BenchmarkClassificationEnum.REAL_HARDWARE],
                measurement_source="nvidia-smi",
                metric_name="test_latency",
                metric_value=15.0,
                metric_unit="ms",
            )
        ],
        reconciliation_table=reconciliation,
    )

    md = BenchmarkReportFormatter.generate_markdown_report(report)
    assert "# Phase AI-18: Performance & Hardware Benchmarking Report" in md
    assert "Windows 11 Enterprise" in md
    assert "AI-04 Real Native Evidence Reconciliation" in md
    assert "POC VERIFIED" in md
    assert "Disclaimer" in md
