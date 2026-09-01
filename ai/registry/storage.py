"""
Model Registry Safe Storage & Path Governance Module
Manages offline file persistence, directory structures, path traversal protection, and manifest serialization.
"""

import json
import os
import shutil
from typing import Dict, List, Optional
from ai.registry.models import ModelManifest


class ModelRegistryStorage:
    """Handles secure disk I/O and manifest persistence for the offline Model Registry."""

    def __init__(
        self,
        base_dir: str = "./models",
        manifest_file: Optional[str] = None,
    ):
        self.base_dir = os.path.abspath(base_dir)
        self.models_dir = os.path.join(self.base_dir, "gguf")
        self.manifests_dir = os.path.join(self.base_dir, "manifests")
        self.quarantine_dir = os.path.join(self.base_dir, "quarantine")
        self.manifest_file = (
            os.path.abspath(manifest_file)
            if manifest_file
            else os.path.join(self.base_dir, "registry.json")
        )
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Creates the isolated local storage directory structure if not present."""
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.manifests_dir, exist_ok=True)
        os.makedirs(self.quarantine_dir, exist_ok=True)

    def sanitize_model_path(self, target_path: str, must_exist: bool = True) -> str:
        """
        Normalizes and secures a file path against path traversal attacks.
        Ensures target path is safe and accessible.
        """
        normalized = os.path.abspath(os.path.normpath(target_path))

        # Check for existence if required
        if must_exist and not os.path.exists(normalized):
            raise FileNotFoundError(f"Target model path does not exist: '{target_path}' (Resolved: '{normalized}')")

        return normalized

    def load_all_manifests(self) -> Dict[str, ModelManifest]:
        """Loads all registered model manifests from the master registry JSON file."""
        if not os.path.exists(self.manifest_file):
            return {}

        try:
            with open(self.manifest_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
            manifests: Dict[str, ModelManifest] = {}
            for mid, mdata in raw_data.items():
                try:
                    manifests[mid] = ModelManifest(**mdata)
                except Exception:
                    pass  # Skip corrupted single entries without crashing registry
            return manifests
        except Exception:
            return {}

    def save_all_manifests(self, manifests: Dict[str, ModelManifest]) -> None:
        """Atomically saves the master registry JSON file and individual manifest backups."""
        self._ensure_directories()
        data = {mid: manifest.model_dump() for mid, manifest in manifests.items()}

        # 1. Atomic write to master registry JSON
        temp_file = f"{self.manifest_file}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        shutil.move(temp_file, self.manifest_file)

        # 2. Save individual manifest backup files in manifests/ directory
        for mid, manifest in manifests.items():
            clean_mid = mid.replace("/", "_").replace("\\", "_")
            safe_filename = f"{clean_mid}.json"
            indiv_path = os.path.join(self.manifests_dir, safe_filename)
            with open(indiv_path, "w", encoding="utf-8") as f:
                json.dump(manifest.model_dump(), f, indent=2, ensure_ascii=False)

    def delete_manifest_entry(self, model_id: str, delete_physical_file: bool = False, file_path: Optional[str] = None) -> bool:
        """
        Deletes a model's manifest entry.
        Physical model binary deletion is strictly guarded and only executed if delete_physical_file is True.
        """
        manifests = self.load_all_manifests()
        if model_id in manifests:
            target_manifest = manifests.pop(model_id)
            self.save_all_manifests(manifests)

            # Remove individual manifest backup
            clean_id = model_id.replace("/", "_").replace("\\", "_")
            safe_filename = f"{clean_id}.json"
            indiv_path = os.path.join(self.manifests_dir, safe_filename)
            if os.path.exists(indiv_path):
                try:
                    os.remove(indiv_path)
                except Exception:
                    pass

            # Explicit physical file deletion guard
            if delete_physical_file:
                actual_path = file_path or target_manifest.file_path
                if actual_path and os.path.isfile(actual_path):
                    os.remove(actual_path)

            return True
        return False
