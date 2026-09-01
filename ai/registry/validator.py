"""
Model Binary & Manifest Static Validator
Performs header magic-byte inspection, streaming SHA-256 verification, and metadata integrity checks.
"""

import hashlib
import os
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from ai.registry.models import (
    ModelCapabilityEnum,
    ModelFormatEnum,
    ModelManifest,
    ModelTaskTypeEnum,
)


class ValidationResult(BaseModel):
    """Structured report produced by ModelValidator."""
    is_valid: bool
    detected_format: Optional[ModelFormatEnum] = None
    actual_file_size_bytes: int = 0
    actual_sha256: str = ""
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ModelValidator:
    """Performs static file inspection, header analysis, and cryptographic validation."""

    GGUF_MAGIC_BYTES = b"GGUF"  # 0x46554747 in ASCII

    @classmethod
    def compute_sha256(cls, file_path: str, chunk_size: int = 65536) -> str:
        """
        Computes SHA-256 hash in streaming 64KB blocks to support multi-gigabyte models
        with near-zero memory footprint.
        """
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"Cannot compute hash: Model file not found at '{file_path}'")

        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def probe_binary_header(cls, file_path: str) -> Tuple[bool, Optional[ModelFormatEnum], str]:
        """
        Reads initial bytes of binary file to detect format and verify magic bytes.
        Returns: (is_readable, detected_format, detail_message)
        """
        if not os.path.exists(file_path):
            return False, None, f"File does not exist: {file_path}"
        if not os.path.isfile(file_path):
            return False, None, f"Path is not a regular file: {file_path}"

        try:
            with open(file_path, "rb") as f:
                header = f.read(16)
        except Exception as e:
            return False, None, f"Unable to read file: {str(e)}"

        if len(header) < 4:
            return False, None, "File too small to contain valid model header (less than 4 bytes)"

        # 1. GGUF Format Check
        if header[:4] == cls.GGUF_MAGIC_BYTES:
            version = int.from_bytes(header[4:8], byteorder="little") if len(header) >= 8 else 0
            return True, ModelFormatEnum.GGUF, f"Valid GGUF container detected (Header version {version})"

        # 2. ONNX Format Check (Protobuf signature or extension)
        if file_path.lower().endswith(".onnx"):
            return True, ModelFormatEnum.ONNX, "ONNX container format by extension"

        # 3. SafeTensors Check
        if file_path.lower().endswith(".safetensors"):
            return True, ModelFormatEnum.SAFE_TENSORS, "SafeTensors container format by extension"

        return False, None, "Unrecognized binary header: Magic bytes do not match supported formats (GGUF/ONNX)"

    @classmethod
    def validate_manifest_static(cls, manifest: ModelManifest) -> ValidationResult:
        """
        Performs comprehensive static validation on a ModelManifest and its underlying file.
        Does NOT execute model inference (execution validation belongs to AI-04).
        """
        errors: List[str] = []
        warnings: List[str] = []
        actual_size = 0
        actual_hash = ""
        detected_format: Optional[ModelFormatEnum] = None

        # 1. File Existence & Readability
        if not os.path.exists(manifest.file_path):
            errors.append(f"Model binary not found at path: '{manifest.file_path}'")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        try:
            actual_size = os.path.getsize(manifest.file_path)
        except Exception as e:
            errors.append(f"Cannot read file size: {str(e)}")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        # 2. Format & Magic Byte Probe
        is_readable, detected_format, detail = cls.probe_binary_header(manifest.file_path)
        if not is_readable:
            errors.append(f"Binary header validation failed: {detail}")
        elif detected_format is not None and manifest.format != detected_format:
            warnings.append(
                f"Manifest format '{manifest.format.value}' differs from probed format '{detected_format.value}'"
            )

        # 3. File Size Validation
        if manifest.file_size_bytes > 0 and actual_size != manifest.file_size_bytes:
            errors.append(
                f"File size mismatch: Manifest declared {manifest.file_size_bytes} bytes, "
                f"actual disk size is {actual_size} bytes."
            )

        # 4. Cryptographic Checksum Integrity
        try:
            actual_hash = cls.compute_sha256(manifest.file_path)
            if manifest.sha256_checksum and actual_hash.lower() != manifest.sha256_checksum.lower():
                errors.append(
                    f"Cryptographic hash mismatch: Manifest declared '{manifest.sha256_checksum}', "
                    f"actual calculated SHA-256 is '{actual_hash}'."
                )
        except Exception as e:
            errors.append(f"Failed to compute SHA-256 checksum: {str(e)}")

        # 5. Task & Capability Specific Checks
        is_embedding = (
            manifest.primary_task_type == ModelTaskTypeEnum.EMBEDDING
            or ModelCapabilityEnum.EMBEDDING in manifest.capabilities
        )
        if is_embedding:
            if not manifest.embedding_dimension or manifest.embedding_dimension <= 0:
                errors.append("Embedding models must explicitly declare a positive integer 'embedding_dimension'.")

        # 6. Context Window Bounds
        if manifest.context_length < 256:
            errors.append(f"Context length '{manifest.context_length}' is unreasonably small (< 256 tokens).")

        return ValidationResult(
            is_valid=(len(errors) == 0),
            detected_format=detected_format,
            actual_file_size_bytes=actual_size,
            actual_sha256=actual_hash,
            errors=errors,
            warnings=warnings,
        )
