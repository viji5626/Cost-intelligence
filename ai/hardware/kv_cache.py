"""
KV Cache Memory Estimation Module
Computes context-sensitive Key-Value tensor cache allocation based on model architecture and quantization.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field


class ArchitectureKVParameters(BaseModel):
    """Architectural parameters required for precise analytical KV cache calculation."""
    num_layers: int
    num_kv_heads: int
    head_dim: int
    bytes_per_element: float = 2.0  # FP16 = 2 bytes, Q8_0 = 1 byte, Q4_0 = 0.5 byte


# Known architecture catalog for exact analytical KV estimation
KNOWN_ARCHITECTURES: Dict[str, ArchitectureKVParameters] = {
    # Qwen2 / Qwen2.5 Family (GQA)
    "qwen2-0.5b": ArchitectureKVParameters(num_layers=24, num_kv_heads=2, head_dim=64, bytes_per_element=2.0),
    "qwen2-1.5b": ArchitectureKVParameters(num_layers=28, num_kv_heads=2, head_dim=128, bytes_per_element=2.0),
    "qwen2-3b": ArchitectureKVParameters(num_layers=36, num_kv_heads=2, head_dim=128, bytes_per_element=2.0),
    "qwen2-7b": ArchitectureKVParameters(num_layers=28, num_kv_heads=4, head_dim=128, bytes_per_element=2.0),
    "qwen2-14b": ArchitectureKVParameters(num_layers=48, num_kv_heads=8, head_dim=128, bytes_per_element=2.0),
    "qwen2.5-3b": ArchitectureKVParameters(num_layers=36, num_kv_heads=2, head_dim=128, bytes_per_element=2.0),
    "qwen2.5-7b": ArchitectureKVParameters(num_layers=28, num_kv_heads=4, head_dim=128, bytes_per_element=2.0),
    "qwen2.5-14b": ArchitectureKVParameters(num_layers=48, num_kv_heads=8, head_dim=128, bytes_per_element=2.0),
    "qwen3-0.6b": ArchitectureKVParameters(num_layers=24, num_kv_heads=4, head_dim=64, bytes_per_element=2.0),
    # Llama 3 / 3.1 Family (GQA)
    "llama3-8b": ArchitectureKVParameters(num_layers=32, num_kv_heads=8, head_dim=128, bytes_per_element=2.0),
    "llama3.1-8b": ArchitectureKVParameters(num_layers=32, num_kv_heads=8, head_dim=128, bytes_per_element=2.0),
    # Mistral Family
    "mistral-7b": ArchitectureKVParameters(num_layers=32, num_kv_heads=8, head_dim=128, bytes_per_element=2.0),
    # Embedding / BERT Models (Encoder only - zero generative KV cache during inference)
    "bert": ArchitectureKVParameters(num_layers=12, num_kv_heads=12, head_dim=64, bytes_per_element=2.0),
}


class KVCacheEstimateResult(BaseModel):
    """Detailed breakdown of estimated KV cache memory."""
    context_length: int
    batch_size: int = 1
    estimated_kv_mb: int
    bytes_per_token: float
    is_exact_analytical: bool
    architecture_matched: Optional[str] = None
    insufficient_metadata: bool = False
    notes: str = ""


class KVCacheEstimator:
    """Computes analytical or heuristic KV cache memory footprint."""

    @classmethod
    def estimate_kv_cache(
        cls,
        context_length: int,
        architecture: Optional[str] = None,
        parameter_count: Optional[str] = None,
        batch_size: int = 1,
        kv_precision_bytes: float = 2.0,
    ) -> KVCacheEstimateResult:
        """
        Calculates KV Cache memory in MB:
        KV_bytes = 2 (K & V) * layers * num_kv_heads * head_dim * context_length * bytes_per_element * batch_size
        """
        arch_key = None
        if architecture:
            norm_arch = architecture.lower().strip()
            # Direct or fuzzy match
            if norm_arch in KNOWN_ARCHITECTURES:
                arch_key = norm_arch
            else:
                for k in KNOWN_ARCHITECTURES:
                    if k in norm_arch:
                        arch_key = k
                        break

        # If architecture is not matched by name, check parameter count heuristics
        if not arch_key and parameter_count:
            norm_param = parameter_count.upper().strip()
            if "3B" in norm_param or "3." in norm_param:
                arch_key = "qwen2-3b"
            elif "7B" in norm_param or "8B" in norm_param:
                arch_key = "qwen2-7b"
            elif "14B" in norm_param:
                arch_key = "qwen2-14b"
            elif "0.6B" in norm_param or "0.5B" in norm_param:
                arch_key = "qwen2-0.5b"

        if arch_key and arch_key in KNOWN_ARCHITECTURES:
            params = KNOWN_ARCHITECTURES[arch_key]
            # Precise analytical calculation
            # bytes_per_token = 2 * layers * kv_heads * head_dim * bytes_per_element * batch_size
            b_per_token = (
                2.0
                * params.num_layers
                * params.num_kv_heads
                * params.head_dim
                * kv_precision_bytes
                * batch_size
            )
            total_bytes = b_per_token * context_length
            total_mb = int(total_bytes / (1024**2))

            return KVCacheEstimateResult(
                context_length=context_length,
                batch_size=batch_size,
                estimated_kv_mb=max(16, total_mb),
                bytes_per_token=round(b_per_token, 2),
                is_exact_analytical=True,
                architecture_matched=arch_key,
                insufficient_metadata=False,
                notes=f"Analytical calculation based on architecture '{arch_key}' ({params.num_layers} layers, {params.num_kv_heads} KV heads)",
            )

        # Fallback Heuristic Calculation (Conservative 110 KB / token for 4K-8K windows)
        heuristic_bytes_per_token = 110.0 * 1024.0 / 1000.0  # ~112 bytes/token
        total_bytes = heuristic_bytes_per_token * context_length * batch_size
        total_mb = int(total_bytes / (1024**2))

        return KVCacheEstimateResult(
            context_length=context_length,
            batch_size=batch_size,
            estimated_kv_mb=max(32, total_mb),
            bytes_per_token=round(heuristic_bytes_per_token, 2),
            is_exact_analytical=False,
            architecture_matched=None,
            insufficient_metadata=True,
            notes="Heuristic estimate used due to insufficient architecture metadata.",
        )
