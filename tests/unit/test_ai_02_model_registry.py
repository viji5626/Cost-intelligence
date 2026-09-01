"""
Phase AI-02 Test Suite: Model Registry, Manifest & Quarantine Engine
Tests offline model onboarding, quarantine state machine, checksum verification, and path security.
"""

import os
import shutil
import tempfile
import pytest
from pydantic import ValidationError

from ai.registry.models import (
    ModelCapabilityEnum,
    ModelFormatEnum,
    ModelManifest,
    ModelRegistrationRequest,
    ModelStatusEnum,
    ModelTaskTypeEnum,
)
from ai.registry.registry_service import ModelRegistryService
from ai.registry.storage import ModelRegistryStorage
from ai.registry.validator import ModelValidator


@pytest.fixture
def temp_registry_env():
    """Creates an isolated temporary sandbox directory for model storage and registry."""
    temp_dir = tempfile.mkdtemp(prefix="hero_ai_registry_test_")
    models_dir = os.path.join(temp_dir, "models")
    manifest_file = os.path.join(temp_dir, "registry.json")

    storage = ModelRegistryStorage(base_dir=models_dir, manifest_file=manifest_file)
    service = ModelRegistryService(storage=storage)

    # Helper function to create synthetic GGUF binary files
    def create_synthetic_gguf(filename: str, content: bytes = b"GGUF\x03\x00\x00\x00synthetic_model_weights_data") -> str:
        fpath = os.path.join(storage.models_dir, filename)
        with open(fpath, "wb") as f:
            f.write(content)
        return fpath

    yield service, storage, create_synthetic_gguf

    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# 1. VALID MODEL ONBOARDING & MANIFEST TESTS
# ==============================================================================

def test_onboard_valid_gguf_generation_model(temp_registry_env):
    """Verifies complete onboarding pipeline for a valid GGUF generation model."""
    service, storage, create_file = temp_registry_env
    file_path = create_file("qwen2.5-3b-q4.gguf")

    req = ModelRegistrationRequest(
        model_id="qwen2.5-3b-instruct-q4_k_m",
        display_name="Qwen 2.5 3B Instruct Q4",
        file_path=file_path,
        primary_task_type=ModelTaskTypeEnum.GENERATION,
        capabilities=[ModelCapabilityEnum.GENERATION, ModelCapabilityEnum.STRUCTURED_OUTPUT],
        architecture="qwen2",
        quantization="Q4_K_M",
        parameter_count="3.09B",
        context_length=4096,
        set_as_default=True,
    )

    manifest = service.onboard_local_model(req, auto_activate_if_valid=True)

    assert manifest.status == ModelStatusEnum.ACTIVE_REGISTERED
    assert manifest.format == ModelFormatEnum.GGUF
    assert len(manifest.sha256_checksum) == 64
    assert manifest.file_size_bytes > 0
    assert manifest.is_default is True

    # Check persistence in registry
    retrieved = service.get_model("qwen2.5-3b-instruct-q4_k_m")
    assert retrieved is not None
    assert retrieved.model_id == "qwen2.5-3b-instruct-q4_k_m"


def test_onboard_valid_embedding_model_with_dimension(temp_registry_env):
    """Verifies onboarding of an embedding model with explicit model-specific dimension."""
    service, storage, create_file = temp_registry_env
    file_path = create_file("qwen3-embed-0.6b.gguf")

    req = ModelRegistrationRequest(
        model_id="qwen3-embedding-0.6b",
        display_name="Qwen 3 Embedding 0.6B",
        file_path=file_path,
        primary_task_type=ModelTaskTypeEnum.EMBEDDING,
        capabilities=[ModelCapabilityEnum.EMBEDDING],
        architecture="qwen3",
        quantization="FP16",
        parameter_count="0.6B",
        embedding_dimension=1024,
        distance_metric="COSINE",
    )

    manifest = service.onboard_local_model(req, auto_activate_if_valid=True)
    assert manifest.status == ModelStatusEnum.ACTIVE_REGISTERED
    assert manifest.embedding_dimension == 1024


# ==============================================================================
# 2. DUPLICATE & VERSION COEXISTENCE TESTS
# ==============================================================================

def test_duplicate_registration_protection(temp_registry_env):
    """Verifies that attempting to register an existing model_id without overwrite raises ValueError."""
    service, storage, create_file = temp_registry_env
    file_path = create_file("model_dup.gguf")

    req = ModelRegistrationRequest(
        model_id="unique-model-001",
        display_name="Unique Model",
        file_path=file_path,
    )
    service.onboard_local_model(req)

    # Attempt second registration with same ID
    manifest_dup = service.get_model("unique-model-001")
    with pytest.raises(ValueError, match="already registered"):
        service.register_manifest(manifest_dup, overwrite=False)


def test_multiple_quantizations_coexist(temp_registry_env):
    """Verifies that different quantizations of the same model coexist as distinct entities."""
    service, storage, create_file = temp_registry_env
    f1 = create_file("qwen2.5-3b-q4.gguf", b"GGUF\x03\x00\x00\x00weights_q4")
    f2 = create_file("qwen2.5-3b-q8.gguf", b"GGUF\x03\x00\x00\x00weights_q8_heavier")

    service.onboard_local_model(
        ModelRegistrationRequest(
            model_id="qwen2.5-3b-q4_k_m",
            display_name="Qwen 3B (Q4_K_M)",
            file_path=f1,
            quantization="Q4_K_M",
        )
    )

    service.onboard_local_model(
        ModelRegistrationRequest(
            model_id="qwen2.5-3b-q8_0",
            display_name="Qwen 3B (Q8_0)",
            file_path=f2,
            quantization="Q8_0",
        )
    )

    models = service.list_models()
    assert len(models) == 2
    ids = [m.model_id for m in models]
    assert "qwen2.5-3b-q4_k_m" in ids
    assert "qwen2.5-3b-q8_0" in ids


# ==============================================================================
# 3. FAILURE INJECTION, CORRUPTION & CHECKSUM TAMPERING TESTS
# ==============================================================================

def test_corrupted_magic_bytes_rejected(temp_registry_env):
    """Failure test: Corrupt file lacking GGUF header -> transitions to REJECTED_INVALID."""
    service, storage, create_file = temp_registry_env
    corrupt_file = create_file("corrupt.bin", b"CORRUPT_NOT_GGUF_HEADER")

    req = ModelRegistrationRequest(
        model_id="corrupt-model-001",
        display_name="Corrupt Model",
        file_path=corrupt_file,
    )

    manifest = service.onboard_local_model(req, auto_activate_if_valid=True)
    assert manifest.status == ModelStatusEnum.REJECTED_INVALID
    assert any("Magic bytes do not match" in err for err in manifest.validation_errors)


def test_missing_embedding_dimension_rejected(temp_registry_env):
    """Failure test: Embedding model missing embedding_dimension fails validation."""
    with pytest.raises(ValidationError):
        ModelManifest(
            model_id="embed-missing-dim",
            display_name="Embed Missing Dim",
            file_path="./models/gguf/test.gguf",
            file_size_bytes=1000,
            sha256_checksum="a" * 64,
            primary_task_type=ModelTaskTypeEnum.EMBEDDING,
            capabilities=[ModelCapabilityEnum.EMBEDDING],
            embedding_dimension=None,  # Missing!
        )


def test_file_tampering_triggers_quarantine(temp_registry_env):
    """Security test: Modifying physical binary on disk triggers quarantine on integrity check."""
    service, storage, create_file = temp_registry_env
    file_path = create_file("tamper_test.gguf", b"GGUF\x03\x00\x00\x00original_weights")

    req = ModelRegistrationRequest(
        model_id="tamper-model-001",
        display_name="Tamper Model",
        file_path=file_path,
    )
    manifest = service.onboard_local_model(req, auto_activate_if_valid=True)
    assert manifest.status == ModelStatusEnum.ACTIVE_REGISTERED

    # Tamper with file on disk
    with open(file_path, "wb") as f:
        f.write(b"GGUF\x03\x00\x00\x00MODIFIED_TAMPERED_WEIGHTS")

    # Verify integrity detects tampering and quarantines model
    is_valid, msg = service.verify_model_integrity("tamper-model-001")
    assert is_valid is False
    assert "Checksum mismatch" in msg

    updated = service.get_model("tamper-model-001")
    assert updated.status == ModelStatusEnum.QUARANTINED
    assert "Checksum mismatch" in updated.quarantine_notes


def test_missing_file_on_disk_triggers_quarantine(temp_registry_env):
    """Failure test: Physical file deleted from disk triggers quarantine on integrity check."""
    service, storage, create_file = temp_registry_env
    file_path = create_file("missing_test.gguf")

    req = ModelRegistrationRequest(
        model_id="missing-file-model",
        display_name="Missing File Model",
        file_path=file_path,
    )
    service.onboard_local_model(req, auto_activate_if_valid=True)

    # Physically delete file
    os.remove(file_path)

    is_valid, msg = service.verify_model_integrity("missing-file-model")
    assert is_valid is False
    assert "missing" in msg.lower()

    updated = service.get_model("missing-file-model")
    assert updated.status == ModelStatusEnum.QUARANTINED


# ==============================================================================
# 4. LIFECYCLE & QUARANTINE STATE TRANSITIONS
# ==============================================================================

def test_quarantine_activation_and_archival_cycle(temp_registry_env):
    """Verifies complete state machine transitions: QUARANTINED -> ACTIVE -> ARCHIVED -> QUARANTINED."""
    service, storage, create_file = temp_registry_env
    file_path = create_file("cycle_model.gguf")

    req = ModelRegistrationRequest(
        model_id="cycle-model-001",
        display_name="Cycle Model",
        file_path=file_path,
    )
    manifest = service.onboard_local_model(req, auto_activate_if_valid=False)
    assert manifest.status == ModelStatusEnum.QUARANTINED

    # 1. Activate
    active = service.activate_model("cycle-model-001")
    assert active.status == ModelStatusEnum.ACTIVE_REGISTERED

    # 2. Deactivate / Archive
    archived = service.deactivate_model("cycle-model-001")
    assert archived.status == ModelStatusEnum.ARCHIVED

    # 3. Quarantine again
    quarantined = service.quarantine_model("cycle-model-001", "Security audit requested quarantine")
    assert quarantined.status == ModelStatusEnum.QUARANTINED
    assert "Security audit" in quarantined.quarantine_notes


# ==============================================================================
# 5. PATH SECURITY & PHYSICAL FILE PRESERVATION
# ==============================================================================

def test_nonexistent_file_path_rejected(temp_registry_env):
    """Security test: Reject onboarding non-existent file."""
    service, storage, _ = temp_registry_env

    req = ModelRegistrationRequest(
        model_id="nonexistent-model",
        display_name="Nonexistent Model",
        file_path="./nonexistent/path/to/model.gguf",
    )
    with pytest.raises(FileNotFoundError):
        service.onboard_local_model(req)


def test_physical_file_deletion_protection(temp_registry_env):
    """Safety test: unregister_model by default does NOT delete physical file unless explicitly instructed."""
    service, storage, create_file = temp_registry_env
    file_path = create_file("preserve_binary.gguf")

    req = ModelRegistrationRequest(
        model_id="preserve-model-001",
        display_name="Preserve Model",
        file_path=file_path,
    )
    service.onboard_local_model(req)

    # 1. Unregister without physical deletion
    service.unregister_model("preserve-model-001", delete_physical_file=False)
    assert service.get_model("preserve-model-001") is None
    assert os.path.isfile(file_path) is True  # Physical file must still exist!

    # 2. Re-register and unregister with physical deletion
    service.onboard_local_model(req)
    service.unregister_model("preserve-model-001", delete_physical_file=True)
    assert os.path.isfile(file_path) is False  # Now physically deleted
