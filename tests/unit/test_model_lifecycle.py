"""
Unit Tests for Model Lifecycle Manager
"""

import pytest
from ai.runtime.lifecycle_manager import ModelLifecycleManager


def test_sequential_model_loading_and_release():
    manager = ModelLifecycleManager(max_vram_mb=8192)

    # 1. Initially clean
    status = manager.get_status()
    assert status["is_memory_clean"] is True

    # 2. Acquire Model A (Embedding)
    loaded_a = manager.acquire_model("EMBEDDING", "Qwen3-Embedding-0.6B", lambda: {"name": "embed_obj"})
    assert manager.active_model == "Qwen3-Embedding-0.6B"
    assert loaded_a["name"] == "embed_obj"

    # 3. Acquire Model B (Reranker) - should unload Model A
    loaded_b = manager.acquire_model("RERANKER", "Qwen3-Reranker-0.6B", lambda: {"name": "rerank_obj"})
    assert manager.active_model == "Qwen3-Reranker-0.6B"
    assert loaded_b["name"] == "rerank_obj"

    # 4. Explicit release
    manager.release_current_model()
    assert manager.active_model is None
    assert manager.get_status()["is_memory_clean"] is True


def test_model_scope_context_manager():
    manager = ModelLifecycleManager()

    with manager.model_scope("SLM", "Qwen2.5-3B", lambda: {"slm": True}) as slm:
        assert slm["slm"] is True
        assert manager.active_model == "Qwen2.5-3B"

    # Outside scope, must be released
    assert manager.active_model is None
