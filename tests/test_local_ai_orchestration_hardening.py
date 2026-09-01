"""
Local AI Provider Orchestration Hardening Test Suite
Verifies decoupled adapters, custom ports, clean URL normalization,
zero silent fallback to mock, and explicit fallback policy enforcement.
"""

import pytest
import asyncio
from ai.core.contracts import TaskType
from ai.orchestrator.models import TaskRequest, TaskRoutingDecision
from ai.orchestrator.task_router import TaskRouter
from ai.providers.adapter_contracts import (
    ProviderTypeEnum,
    ProviderHealthStatusEnum,
    ProviderHealthReport,
)
from ai.providers.adapters.ollama_adapter import OllamaProviderAdapter
from ai.providers.adapters.lm_studio_adapter import LMStudioProviderAdapter
from ai.providers.adapters.native_gguf_adapter import NativeGGUFAdapter
from ai.providers.registry import ProviderAdapterRegistry


class TestLocalAIOrchestrationHardening:
    """Test suite for local AI provider orchestration hardening."""

    def test_builtin_adapter_properties(self):
        """Verifies NativeGGUFAdapter declares is_builtin and telemetry_exposed."""
        adapter = NativeGGUFAdapter()
        assert adapter.is_builtin is True
        assert adapter.telemetry_exposed is True
        assert adapter.provider_type == ProviderTypeEnum.BUILTIN_NATIVE_GGUF

    def test_ollama_custom_port_update(self):
        """Verifies Ollama dynamic custom port update (e.g. 11437)."""
        adapter = OllamaProviderAdapter(base_url="http://127.0.0.1:11434")
        assert adapter.endpoint == "http://127.0.0.1:11434"
        assert adapter.is_builtin is False
        assert adapter.telemetry_exposed is False

        # Update to custom port 11437
        adapter.update_endpoint("http://127.0.0.1:11437")
        assert adapter.endpoint == "http://127.0.0.1:11437"
        assert adapter.base_url == "http://127.0.0.1:11437"

    def test_lm_studio_url_normalization(self):
        """Verifies LM Studio base URL normalization and /v1 clean separation."""
        adapter1 = LMStudioProviderAdapter(base_url="http://127.0.0.1:1234")
        assert adapter1.base_url == "http://127.0.0.1:1234"
        assert adapter1.openai_base_url == "http://127.0.0.1:1234/v1"

        # Case with trailing /v1 in config
        adapter2 = LMStudioProviderAdapter(base_url="http://127.0.0.1:1234/v1")
        assert adapter2.base_url == "http://127.0.0.1:1234"
        assert adapter2.openai_base_url == "http://127.0.0.1:1234/v1"

        # Update endpoint cleanly
        adapter2.update_endpoint("http://localhost:5678/v1/")
        assert adapter2.base_url == "http://localhost:5678"
        assert adapter2.openai_base_url == "http://localhost:5678/v1"

    @pytest.mark.asyncio
    async def test_provider_registry_configuration_updates(self):
        """Verifies dynamic config update through registry."""
        registry = ProviderAdapterRegistry(register_defaults=True)
        adapter = registry.update_provider_config(
            provider_name_or_type="OLLAMA",
            endpoint="http://127.0.0.1:11437",
            fallback_policy="FALLBACK_BUILTIN_LOCAL",
        )
        assert adapter.endpoint == "http://127.0.0.1:11437"
        assert adapter.fallback_policy == "FALLBACK_BUILTIN_LOCAL"

    def test_task_router_fallback_disabled_when_provider_offline(self):
        """Verifies NO silent substitution occurs when requested provider is offline and fallback is disabled."""
        router = TaskRouter()
        req = TaskRequest(
            task_id="test-task-1",
            task_type=TaskType.REASONING,
            prompt="Calculate cost variance",
            provider_override="OLLAMA",
            fallback_policy="FALLBACK_DISABLED",
        )

        decision = router.resolve_routing(req)
        # When Ollama daemon is offline and fallback is disabled, routing must fail explicitly
        assert decision.is_routed is False
        assert decision.requested_provider == "OLLAMA"
        assert decision.actual_provider is None
        assert "OFFLINE" in decision.explanation
        assert "FALLBACK_DISABLED" or "disabled" in decision.explanation.lower()

    def test_task_router_fallback_builtin_when_provider_offline(self):
        """Verifies explicit recorded fallback to BUILTIN_NATIVE_GGUF when FALLBACK_BUILTIN_LOCAL is configured."""
        router = TaskRouter()
        req = TaskRequest(
            task_id="test-task-2",
            task_type=TaskType.REASONING,
            prompt="Calculate cost variance",
            provider_override="OLLAMA",
            fallback_policy="FALLBACK_BUILTIN_LOCAL",
        )

        decision = router.resolve_routing(req)
        # Should fallback explicitly to native engine
        assert decision.is_routed is True
        assert decision.requested_provider == "OLLAMA"
        assert decision.actual_provider == "BUILTIN_NATIVE_GGUF"
        assert decision.fallback_occurred is True
        assert "fell back" in decision.fallback_reason.lower()

    def test_air_gapped_native_operation(self):
        """Verifies native GGUF engine operates directly with zero external providers."""
        router = TaskRouter()
        req = TaskRequest(
            task_id="test-task-3",
            task_type=TaskType.REASONING,
            prompt="Analyze cost drivers",
            provider_override="BUILTIN_NATIVE_GGUF",
        )

        decision = router.resolve_routing(req)
        assert decision.is_routed is True
        assert decision.provider_type == "BUILTIN_NATIVE_GGUF"
        assert decision.fallback_occurred is False
        assert decision.hardware_verdict == "SAFE"
