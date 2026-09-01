"""
Provider Adapter Registry
Manages registration, discovery, task capability resolution, and health aggregation across all local provider adapters.
Strictly separates Provider identity from Model identity (managed by ModelRegistry).
"""

import asyncio
from typing import Any, Dict, List, Optional

from ai.core.contracts import TaskType
from ai.providers.adapter_contracts import (
    BaseProviderAdapter,
    EmbeddingAdapter,
    InferenceAdapter,
    ProviderHealthReport,
    ProviderHealthStatusEnum,
    ProviderTypeEnum,
    RerankerAdapter,
    VisionOCRAdapter,
)
from ai.providers.adapters.lm_studio_adapter import LMStudioProviderAdapter
from ai.providers.adapters.local_vision_ocr_adapter import LocalVisionOCRAdapter
from ai.providers.adapters.mock_simulation_adapter import MockSimulationAdapter
from ai.providers.adapters.native_embedding_adapter import NativeEmbeddingAdapter
from ai.providers.adapters.native_gguf_adapter import NativeGGUFAdapter
from ai.providers.adapters.native_reranker_adapter import NativeRerankerAdapter
from ai.providers.adapters.ollama_adapter import OllamaProviderAdapter
from ai.providers.adapters.openai_compatible_adapter import LocalOpenAICompatibleAdapter
from ai.providers.exceptions import AIProviderError


class ProviderAdapterRegistry:
    """
    Central registry for discovering, selecting, and probing local AI provider adapters.
    """

    def __init__(self, register_defaults: bool = True):
        self._adapters: Dict[str, BaseProviderAdapter] = {}
        self._default_adapters: Dict[TaskType, str] = {}
        if register_defaults:
            self._register_default_adapters()

    def _register_default_adapters(self) -> None:
        """Instantiates and registers standard local provider adapters."""
        # Built-in native engines (Primary default)
        gguf = NativeGGUFAdapter()
        embed = NativeEmbeddingAdapter()
        rerank = NativeRerankerAdapter()
        vision = LocalVisionOCRAdapter()

        # Optional local daemon adapters
        ollama = OllamaProviderAdapter()
        lm_studio = LMStudioProviderAdapter()
        openai_compat = LocalOpenAICompatibleAdapter()

        self.register_adapter(gguf, make_default_for=[
            TaskType.REASONING,
            TaskType.GROUNDED_REASONING,
            TaskType.STRUCTURED_EXTRACTION,
            TaskType.CLASSIFICATION,
            TaskType.SUMMARIZATION,
            TaskType.TOOL_CALL,
        ])
        self.register_adapter(embed, make_default_for=[TaskType.EMBEDDING])
        self.register_adapter(rerank, make_default_for=[TaskType.RERANKING])
        self.register_adapter(vision, make_default_for=[TaskType.VISION_OCR])

        self.register_adapter(ollama)
        self.register_adapter(lm_studio)
        self.register_adapter(openai_compat)

    def register_adapter(
        self,
        adapter: BaseProviderAdapter,
        make_default_for: Optional[List[TaskType]] = None,
    ) -> None:
        """Registers a provider adapter by name and provider type."""
        self._adapters[adapter.name] = adapter
        # Also map by provider_type string if not taken by primary
        type_key = adapter.provider_type.value
        if type_key not in self._adapters:
            self._adapters[type_key] = adapter

        if make_default_for:
            for task in make_default_for:
                self._default_adapters[task] = adapter.name

    def unregister_adapter(self, name_or_type: str) -> bool:
        """Unregisters an adapter by name or provider type."""
        removed = False
        adapter = self._adapters.pop(name_or_type, None)
        if adapter:
            removed = True
            # Clean up default pointers
            for task, def_name in list(self._default_adapters.items()):
                if def_name == adapter.name:
                    del self._default_adapters[task]
            # Clean up aliased keys
            for k, v in list(self._adapters.items()):
                if v == adapter:
                    del self._adapters[k]
        return removed

    def get_adapter(self, name_or_type: str) -> Optional[BaseProviderAdapter]:
        """Looks up an adapter by exact name or ProviderTypeEnum value."""
        return self._adapters.get(name_or_type)

    def get_default_adapter_for_task(self, task_type: TaskType) -> Optional[BaseProviderAdapter]:
        """Returns the default registered adapter for a given task type."""
        name = self._default_adapters.get(task_type)
        if name:
            return self._adapters.get(name)
        # Fallback: search any adapter supporting the task
        for adapter in self.list_adapters():
            if task_type in adapter.supported_tasks():
                return adapter
        return None

    def list_adapters(self) -> List[BaseProviderAdapter]:
        """Returns a deduplicated list of all registered provider adapters."""
        seen = set()
        unique = []
        for adapter in self._adapters.values():
            if adapter.name not in seen:
                seen.add(adapter.name)
                unique.append(adapter)
        return unique

    def discover_adapters_for_task(self, task_type: TaskType) -> List[BaseProviderAdapter]:
        """Discovers all registered adapters that support a given task type."""
        return [ad for ad in self.list_adapters() if task_type in ad.supported_tasks()]

    async def get_health_summary(self, active_probe: bool = False) -> Dict[str, ProviderHealthReport]:
        """Collects passive or active health reports from all registered provider adapters."""
        reports: Dict[str, ProviderHealthReport] = {}
        for adapter in self.list_adapters():
            if active_probe:
                report = await adapter.active_health_probe()
            else:
                report = await adapter.passive_health_probe()
            reports[adapter.name] = report
        return reports

    def update_provider_config(
        self,
        provider_name_or_type: str,
        endpoint: str,
        fallback_policy: Optional[str] = None,
        **kwargs: Any,
    ) -> BaseProviderAdapter:
        """Dynamically updates an adapter's endpoint URL / custom port and fallback policy."""
        adapter = self.get_adapter(provider_name_or_type)
        if not adapter:
            raise AIProviderError(
                message=f"Provider '{provider_name_or_type}' is not registered.",
                provider_name=provider_name_or_type,
            )
        adapter.update_endpoint(base_url=endpoint, **kwargs)
        if fallback_policy:
            adapter.fallback_policy = fallback_policy
        return adapter

    async def test_connection(self, provider_name_or_type: str) -> ProviderHealthReport:
        """Executes a live probe for the specified provider adapter."""
        adapter = self.get_adapter(provider_name_or_type)
        if not adapter:
            return ProviderHealthReport(
                provider_name=provider_name_or_type,
                provider_type=ProviderTypeEnum.OPENAI_COMPATIBLE,
                status=ProviderHealthStatusEnum.OFFLINE,
                last_error=f"Provider '{provider_name_or_type}' not found in registry.",
                probe_type="PASSIVE",
            )
        return await adapter.passive_health_probe()

    async def get_provider_models(self, provider_name_or_type: str) -> List[Dict[str, Any]]:
        """Queries model list from the specified provider without merging identities."""
        adapter = self.get_adapter(provider_name_or_type)
        if not adapter:
            return []

        if adapter.provider_type == ProviderTypeEnum.BUILTIN_NATIVE_GGUF:
            from ai.registry.registry_service import model_registry_service
            models = []
            for m in model_registry_service.list_models():
                if m.status.value == "ACTIVE_REGISTERED":
                    models.append({
                        "model_id": m.model_id,
                        "display_name": m.display_name,
                        "provider": adapter.name,
                        "provider_type": adapter.provider_type.value,
                        "status": "AVAILABLE",
                        "endpoint": adapter.endpoint or "in-process",
                        "format": m.format.value,
                        "quantization": m.quantization,
                        "parameter_count": m.parameter_count,
                        "context_length": m.context_length,
                        "capabilities": [c.value for c in m.capabilities],
                        "source": "AI-02 Model Registry",
                    })
            return models

        probe = await adapter.passive_health_probe()
        models = []
        raw_models = probe.details.get("models", [])
        raw_by_name = {m.get("name") or m.get("id"): m for m in raw_models if isinstance(m, dict)}

        for m in probe.available_models:
            raw_meta = raw_by_name.get(m, {})
            models.append({
                "model_id": m,
                "display_name": m,
                "provider": adapter.name,
                "provider_type": adapter.provider_type.value,
                "status": "AVAILABLE" if probe.status == ProviderHealthStatusEnum.HEALTHY else "UNAVAILABLE",
                "endpoint": adapter.endpoint,
                "source": f"{adapter.name} local endpoint",
                "size_bytes": raw_meta.get("size") if isinstance(raw_meta, dict) else None,
                "format": raw_meta.get("details", {}).get("format") if isinstance(raw_meta, dict) and isinstance(raw_meta.get("details"), dict) else "GGUF",
            })
        return models


# Global singleton instance
provider_registry = ProviderAdapterRegistry(register_defaults=True)
