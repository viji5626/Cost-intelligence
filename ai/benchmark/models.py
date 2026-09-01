"""Phase AI-18: Performance & Hardware Benchmark Data Models

Defines structured containers, measurement classifications, statistical summaries,
and provenance attribution for local air-gapped runtime and hardware benchmarking.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BenchmarkClassificationEnum(str, Enum):
    REAL_HARDWARE = "REAL_HARDWARE"
    REAL_LOCAL_RUNTIME = "REAL_LOCAL_RUNTIME"
    SYNTHETIC_DATA = "SYNTHETIC_DATA"
    SIMULATED = "SIMULATED"


class BenchmarkCategoryEnum(str, Enum):
    BM1_HARDWARE_FIT = "BM-1: Hardware Fit & KV Cache Budget"
    BM2_NATIVE_INFERENCE = "BM-2: Native Inference Latency & Throughput"
    BM3_RETRIEVAL_SCALE = "BM-3: Hybrid Retrieval & Cross-Encoder Scale"
    BM4_MODEL_LIFECYCLE = "BM-4: Sequential Model Lifecycle & Memory Stability"
    BM5_OCR_EXTRACTION = "BM-5: Digital PDF vs Raster Image OCR"
    BM6_GBNF_VALIDATION = "BM-6: GBNF Grammar Compilation & Validation"
    BM7_API_CONCURRENCY = "BM-7: Local API Concurrency & Queueing Stress"
    FAILURE_MODES = "Failure Mode Measurements"
    AI04_RECONCILIATION = "AI-04 Native GGUF Evidence Reconciliation"


class StatisticalMetric(BaseModel):
    """Statistical summary across multiple benchmark repetitions."""
    count: int = Field(default=1, ge=1)
    min_val: float
    mean_val: float
    p50_val: float
    p95_val: float
    max_val: float
    unit: str = "ms"

    @classmethod
    def from_samples(cls, samples: List[float], unit: str = "ms") -> "StatisticalMetric":
        if not samples:
            return cls(count=1, min_val=0.0, mean_val=0.0, p50_val=0.0, p95_val=0.0, max_val=0.0, unit=unit)
        sorted_samples = sorted(samples)
        n = len(sorted_samples)
        min_v = round(sorted_samples[0], 4)
        max_v = round(sorted_samples[-1], 4)
        mean_v = round(sum(sorted_samples) / n, 4)
        
        # Calculate percentiles
        p50_idx = int(n * 0.50)
        p95_idx = min(int(n * 0.95), n - 1)
        p50_v = round(sorted_samples[p50_idx], 4)
        p95_v = round(sorted_samples[p95_idx], 4) if n > 1 else max_v

        return cls(
            count=n,
            min_val=min_v,
            mean_val=mean_v,
            p50_val=p50_v,
            p95_val=p95_v,
            max_val=max_v,
            unit=unit,
        )


class SingleBenchmarkMeasurement(BaseModel):
    """An individual benchmark trial record with classifications, provenance, and measurement source."""
    benchmark_name: str
    category: BenchmarkCategoryEnum
    classifications: List[BenchmarkClassificationEnum]
    measurement_source: str = "perf_counter_ns"  # nvidia-smi, psutil, llama.cpp timing output, HTTP client timing, perf_counter_ns
    runtime_identity: Dict[str, Any] = Field(default_factory=dict)
    status: str = "SUCCESS"  # SUCCESS, EXECUTED, QUEUED, REJECTED, NOT_AVAILABLE, SIMULATED
    metric_name: str
    metric_value: Optional[float] = None
    metric_unit: str = "ms"
    stats: Optional[StatisticalMetric] = None
    telemetry: Dict[str, Any] = Field(default_factory=dict)
    notes: str = ""


class HardwareEnvironmentBaseline(BaseModel):
    """System hardware and runtime specification snapshot recorded at benchmark start."""
    os_name: str = "Windows 11 Enterprise"
    os_build: str = "26200"
    os_raw: str = "Windows 10.0.26200"
    python_version: str = "3.14.3"
    cpu_model: str = "AMD64 (12 Physical / 24 Logical Cores)"
    cpu_physical_cores: int = 12
    cpu_logical_cores: int = 24
    ram_total_gb: float = 15.12
    ram_available_gb: float = 0.8
    gpu_model: str = "NVIDIA GeForce RTX 4060 Laptop GPU"
    vram_total_mb: float = 8192.0
    vram_free_mb: float = 7864.0
    nvidia_driver_version: str = "Driver 610.47"
    cuda_version: str = "12.4"
    active_runtime_profile: str = "TIER1_LOW (Balanced)"
    benchmark_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AI04ReconciliationRecord(BaseModel):
    """Reconciliation record comparing AI-04 native physical GGUF evidence with AI-18 benchmark suite."""
    metric_name: str
    ai04_native_physical_evidence: str
    ai18_observed_measurement: str
    runtime_state: str
    measurement_source: str
    reconciliation_explanation: str


class ComprehensiveBenchmarkReport(BaseModel):
    """Master benchmark report document encompassing all measurements, classifications, and reconciliation."""
    report_id: str
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    hardware_baseline: HardwareEnvironmentBaseline
    disclaimer: str = (
        "These measurements characterize the POC environment and synthetic test conditions. "
        "They are not production SLAs or capacity guarantees."
    )
    measurements: List[SingleBenchmarkMeasurement] = Field(default_factory=list)
    reconciliation_table: List[AI04ReconciliationRecord] = Field(default_factory=list)
    final_assessment: str = "POC VERIFIED"
    limitations: List[str] = Field(default_factory=list)
