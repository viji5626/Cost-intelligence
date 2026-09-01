"""
Model Registry Service
Orchestrates offline model onboarding, quarantine state machine, checksum integrity, and model manifest management.
"""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from ai.core.config import ai_settings
from ai.registry.models import (
    ModelCapabilityEnum,
    ModelFormatEnum,
    ModelManifest,
    ModelRegistrationRequest,
    ModelStatusEnum,
    ModelTaskTypeEnum,
)
from ai.registry.storage import ModelRegistryStorage
from ai.registry.validator import ModelValidator, ValidationResult


class ModelRegistryService:
    """Manages the lifecycle, static validation, quarantine pool, and metadata of all local models."""

    def __init__(self, storage: Optional[ModelRegistryStorage] = None):
        self.storage = storage or ModelRegistryStorage(
            base_dir=ai_settings.MODEL_STORAGE_PATH,
            manifest_file=ai_settings.MANIFEST_STORAGE_PATH,
        )

    def list_models(
        self,
        task_type: Optional[ModelTaskTypeEnum] = None,
        status: Optional[ModelStatusEnum] = None,
        capability: Optional[ModelCapabilityEnum] = None,
    ) -> List[ModelManifest]:
        """Lists registered models filtered by task type, status, and/or specific capability."""
        manifests = self.storage.load_all_manifests()
        results: List[ModelManifest] = []

        for m in manifests.values():
            if status is not None and m.status != status:
                continue
            if task_type is not None and m.primary_task_type != task_type:
                continue
            if capability is not None and capability not in m.capabilities:
                continue
            results.append(m)

        return sorted(results, key=lambda x: (not x.is_default, x.model_id))

    def get_model(self, model_id: str) -> Optional[ModelManifest]:
        """Retrieves a model manifest by model_id."""
        manifests = self.storage.load_all_manifests()
        return manifests.get(model_id)

    def register_manifest(self, manifest: ModelManifest, overwrite: bool = False) -> ModelManifest:
        """Registers a completed ModelManifest with duplicate collision protection."""
        manifests = self.storage.load_all_manifests()

        if manifest.model_id in manifests and not overwrite:
            raise ValueError(
                f"Model with ID '{manifest.model_id}' is already registered. "
                "Use distinct version/quantization ID or set overwrite=True."
            )

        manifest.updated_at = datetime.now(timezone.utc).isoformat()
        manifests[manifest.model_id] = manifest
        self.storage.save_all_manifests(manifests)
        return manifest

    def onboard_local_model(
        self,
        request: ModelRegistrationRequest,
        auto_activate_if_valid: bool = True,
    ) -> ModelManifest:
        """
        Onboards a local binary file through the Quarantine State Machine:
        1. Sanitize file path (path traversal protection)
        2. Probe binary header (magic bytes)
        3. Stream calculate SHA-256 checksum
        4. Create ModelManifest in QUARANTINED state
        5. Run static validation suite
        6. Transition to ACTIVE_REGISTERED (if valid & auto_activate) or REJECTED_INVALID
        """
        sanitized_path = self.storage.sanitize_model_path(request.file_path, must_exist=True)
        file_size = os.path.getsize(sanitized_path)

        # 1. Probe binary format and header
        is_readable, detected_format, header_msg = ModelValidator.probe_binary_header(sanitized_path)
        format_enum = detected_format or ModelFormatEnum.GGUF

        # 2. Compute SHA-256
        sha256 = ModelValidator.compute_sha256(sanitized_path)

        # 3. Construct Initial Manifest in QUARANTINED state
        manifest = ModelManifest(
            model_id=request.model_id,
            display_name=request.display_name,
            file_path=sanitized_path,
            file_size_bytes=file_size,
            sha256_checksum=sha256,
            format=format_enum,
            quantization=request.quantization,
            architecture=request.architecture,
            parameter_count=request.parameter_count,
            context_length=request.context_length,
            recommended_context_length=min(request.context_length, 4096),
            primary_task_type=request.primary_task_type,
            capabilities=request.capabilities,
            embedding_dimension=request.embedding_dimension,
            distance_metric=request.distance_metric,
            supports_gbnf_grammar=request.supports_gbnf_grammar,
            supports_streaming=request.supports_streaming,
            supports_vision=request.supports_vision,
            estimated_ram_mb=request.estimated_ram_mb or int(file_size / (1024**2) * 1.2),
            estimated_vram_mb=request.estimated_vram_mb or int(file_size / (1024**2)),
            status=ModelStatusEnum.QUARANTINED,
            is_default=request.set_as_default,
            quarantine_notes=f"Initial onboarding. Header probe: {header_msg}",
        )

        # 4. Save quarantined manifest
        self.register_manifest(manifest, overwrite=True)

        # 5. Run Static Validation
        val_result = ModelValidator.validate_manifest_static(manifest)

        manifests = self.storage.load_all_manifests()
        if val_result.is_valid:
            manifest.status = (
                ModelStatusEnum.ACTIVE_REGISTERED
                if auto_activate_if_valid
                else ModelStatusEnum.QUARANTINED
            )
            manifest.validation_errors = []
            manifest.quarantine_notes = "Static validation passed successfully."
        else:
            manifest.status = ModelStatusEnum.REJECTED_INVALID
            manifest.validation_errors = val_result.errors
            manifest.quarantine_notes = f"Validation failed: {'; '.join(val_result.errors)}"

        manifest.updated_at = datetime.now(timezone.utc).isoformat()
        manifests[manifest.model_id] = manifest
        self.storage.save_all_manifests(manifests)

        return manifest

    def validate_model(self, model_id: str) -> ValidationResult:
        """Triggers on-demand static validation on an existing registered model."""
        manifest = self.get_model(model_id)
        if not manifest:
            raise KeyError(f"Model '{model_id}' not found in registry.")

        val_result = ModelValidator.validate_manifest_static(manifest)
        manifests = self.storage.load_all_manifests()

        if val_result.is_valid:
            manifest.status = ModelStatusEnum.ACTIVE_REGISTERED
            manifest.validation_errors = []
            manifest.quarantine_notes = "On-demand static validation passed."
        else:
            manifest.status = ModelStatusEnum.REJECTED_INVALID
            manifest.validation_errors = val_result.errors
            manifest.quarantine_notes = f"Validation failed: {'; '.join(val_result.errors)}"

        manifest.updated_at = datetime.now(timezone.utc).isoformat()
        manifests[model_id] = manifest
        self.storage.save_all_manifests(manifests)

        return val_result

    def quarantine_model(self, model_id: str, reason: str) -> ModelManifest:
        """Manually or automatically moves a model to the QUARANTINED state."""
        manifest = self.get_model(model_id)
        if not manifest:
            raise KeyError(f"Model '{model_id}' not found in registry.")

        manifest.status = ModelStatusEnum.QUARANTINED
        manifest.quarantine_notes = reason
        manifest.updated_at = datetime.now(timezone.utc).isoformat()

        manifests = self.storage.load_all_manifests()
        manifests[model_id] = manifest
        self.storage.save_all_manifests(manifests)
        return manifest

    def activate_model(self, model_id: str) -> ModelManifest:
        """Activates a model if its static validation is verified."""
        manifest = self.get_model(model_id)
        if not manifest:
            raise KeyError(f"Model '{model_id}' not found in registry.")

        val_result = ModelValidator.validate_manifest_static(manifest)
        if not val_result.is_valid:
            raise ValueError(
                f"Cannot activate model '{model_id}': Static validation failed ({'; '.join(val_result.errors)})"
            )

        manifest.status = ModelStatusEnum.ACTIVE_REGISTERED
        manifest.validation_errors = []
        manifest.updated_at = datetime.now(timezone.utc).isoformat()

        manifests = self.storage.load_all_manifests()
        manifests[model_id] = manifest
        self.storage.save_all_manifests(manifests)
        return manifest

    def deactivate_model(self, model_id: str) -> ModelManifest:
        """Archives/deactivates a model so it is no longer selected for active tasks."""
        manifest = self.get_model(model_id)
        if not manifest:
            raise KeyError(f"Model '{model_id}' not found in registry.")

        manifest.status = ModelStatusEnum.ARCHIVED
        manifest.updated_at = datetime.now(timezone.utc).isoformat()

        manifests = self.storage.load_all_manifests()
        manifests[model_id] = manifest
        self.storage.save_all_manifests(manifests)
        return manifest

    def verify_model_integrity(self, model_id: str) -> Tuple[bool, str]:
        """
        Verifies live file integrity against the registered SHA-256 hash.
        If file on disk was modified, tampered with, or corrupted, automatically moves model to QUARANTINED.
        """
        manifest = self.get_model(model_id)
        if not manifest:
            return False, f"Model '{model_id}' not found in registry."

        if not os.path.isfile(manifest.file_path):
            self.quarantine_model(model_id, "Physical binary file missing on disk.")
            return False, f"File missing at path '{manifest.file_path}'"

        current_hash = ModelValidator.compute_sha256(manifest.file_path)
        if current_hash.lower() != manifest.sha256_checksum.lower():
            self.quarantine_model(
                model_id,
                f"Checksum mismatch on disk! Registered '{manifest.sha256_checksum[:8]}...', Found '{current_hash[:8]}...'",
            )
            return False, "Checksum mismatch: Binary file on disk has changed."

        return True, "Checksum integrity verified."

    def unregister_model(self, model_id: str, delete_physical_file: bool = False) -> bool:
        """Removes a model's registration. Physical deletion requires explicit parameter."""
        manifest = self.get_model(model_id)
        if not manifest:
            return False
        return self.storage.delete_manifest_entry(
            model_id=model_id,
            delete_physical_file=delete_physical_file,
            file_path=manifest.file_path,
        )


# Global singleton instance
model_registry_service = ModelRegistryService()
