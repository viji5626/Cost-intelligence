"""
Unit Tests for Retrieval Benchmark Dataset & Harness
"""

import pytest
from ai.retrieval.benchmark import RetrievalBenchmarkHarness


def test_retrieval_benchmark_execution():
    result = RetrievalBenchmarkHarness.run_benchmark()

    assert result.total_queries == 10
    # Recall@3 should be high across the multi-channel hybrid engine
    assert result.recall_at_3 >= 0.80
    assert result.recall_at_5 >= 0.80
    assert result.precision_at_3 >= 0.80
    assert result.p50_latency_ms < 50.0  # Fast deterministic hybrid search
    assert len(result.scenario_details) == 10
