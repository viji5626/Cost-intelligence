from typing import Any, Dict, List, Optional
from ai.core.contracts import ModelManifestData, ModelStatusEnum, TaskType
from ai.registry.models import ModelCapabilityEnum, ModelTaskTypeEnum
from ai.registry.registry_service import ModelRegistryService, model_registry_service


class ManifestRegistry:
    """
    Registry holding registered active and quarantined model manifests.
    """

    def __init__(self, registry_service: Optional[ModelRegistryService] = None):
        self.service = registry_service or model_registry_service
        self._in_memory: Dict[str, ModelManifestData] = {}

    def _map_manifest_to_data(self, m: Any) -> ModelManifestData:
        tasks: List[TaskType] = []
        if getattr(m, "primary_task_type", None) == ModelTaskTypeEnum.EMBEDDING:
            tasks.append(TaskType.EMBEDDING)
        elif getattr(m, "primary_task_type", None) == ModelTaskTypeEnum.RERANKER:
            tasks.append(TaskType.RERANKING)
        elif getattr(m, "primary_task_type", None) == ModelTaskTypeEnum.VISION_OCR:
            tasks.append(TaskType.VISION_OCR)
        else:
            tasks.append(TaskType.REASONING)

        for c in getattr(m, "capabilities", []):
            if c == ModelCapabilityEnum.EMBEDDING and TaskType.EMBEDDING not in tasks:
                tasks.append(TaskType.EMBEDDING)
            elif c == ModelCapabilityEnum.RERANKING and TaskType.RERANKING not in tasks:
                tasks.append(TaskType.RERANKING)
            elif c == ModelCapabilityEnum.GENERATION and TaskType.REASONING not in tasks:
                tasks.append(TaskType.REASONING)

        return ModelManifestData(
            model_id=m.model_id,
            model_version=m.version,
            display_name=m.display_name,
            file_path=m.file_path,
            file_size_bytes=m.file_size_bytes,
            sha256_checksum=m.sha256_checksum,
            format=m.format.value if hasattr(m.format, "value") else str(m.format),
            quantization=m.quantization,
            architecture=m.architecture,
            parameter_count=m.parameter_count,
            supported_tasks=tasks,
            status=m.status.value if hasattr(m.status, "value") else str(m.status),
        )

    def register_manifest(self, manifest: ModelManifestData) -> None:
        """Registers a model manifest in memory."""
        self._in_memory[manifest.model_id] = manifest

    def get_model(self, model_id: str) -> Optional[ModelManifestData]:
        """Retrieves a model manifest by ID."""
        if model_id in self._in_memory:
            return self._in_memory[model_id]
        if self.service:
            m = self.service.get_model(model_id)
            if m:
                return self._map_manifest_to_data(m)
        return None

    def list_models(self) -> List[ModelManifestData]:
        """Lists all registered models."""
        models = list(self._in_memory.values())
        if self.service:
            persisted = self.service.list_models()
            for m in persisted:
                if m.model_id not in self._in_memory:
                    models.append(self._map_manifest_to_data(m))
        return models
