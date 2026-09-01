"""
Document Decoding & Safety Inspection Module (AI-15)
Performs strict magic-byte format identification, MIME consistency verification,
decompression bomb prevention, and resource bound enforcement for visual documents.
"""

import hashlib
import io
import time
from typing import Optional, Tuple
from PIL import Image
import pypdf

from ai.providers.exceptions import InputValidationError
from ai.vision.models import ImageFormatEnum


class DocumentDecoder:
    """
    Decodes and validates document and image streams with security bounds.
    """

    MAX_DOCUMENT_BYTES = 25 * 1024 * 1024  # 25 MB max
    MAX_IMAGE_WIDTH = 8192
    MAX_IMAGE_HEIGHT = 8192
    MAX_IMAGE_PIXELS = 64_000_000  # 64 MP (Decompression bomb protection)
    MAX_PDF_PAGES = 50

    @classmethod
    def identify_format(cls, data: bytes) -> ImageFormatEnum:
        """Inspects binary magic bytes to determine file format."""
        if not data or len(data) < 4:
            return ImageFormatEnum.UNKNOWN

        # PNG: \x89PNG\r\n\x1a\n
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return ImageFormatEnum.PNG

        # JPEG: \xff\xd8\xff
        if data.startswith(b"\xff\xd8\xff"):
            return ImageFormatEnum.JPEG

        # PDF: %PDF-
        if data.startswith(b"%PDF-"):
            return ImageFormatEnum.PDF

        # TIFF: II*\x00 (little endian) or MM\x00* (big endian)
        if data.startswith(b"II*\x00") or data.startswith(b"MM\x00*"):
            return ImageFormatEnum.TIFF

        # BMP: BM
        if data.startswith(b"BM"):
            return ImageFormatEnum.BMP

        # WebP: RIFF....WEBP
        if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return ImageFormatEnum.WEBP

        return ImageFormatEnum.UNKNOWN

    @classmethod
    def validate_and_decode(
        cls,
        data: bytes,
        declared_mime_type: Optional[str] = None,
    ) -> Tuple[ImageFormatEnum, dict]:
        """
        Validates data size, magic bytes, MIME consistency, and safety dimensions.
        Returns format enum and metadata dictionary (dimensions, pages, sha256).
        """
        if not data:
            raise InputValidationError(
                message="Document byte stream cannot be empty.",
                provider_name="document-decoder",
            )

        # 1. Byte Size Limit Check
        if len(data) > cls.MAX_DOCUMENT_BYTES:
            raise InputValidationError(
                message=f"Document exceeds maximum size limit of {cls.MAX_DOCUMENT_BYTES // (1024*1024)}MB (Provided: {len(data) // (1024*1024)}MB).",
                provider_name="document-decoder",
            )

        doc_hash = hashlib.sha256(data).hexdigest()
        detected_format = cls.identify_format(data)

        if detected_format == ImageFormatEnum.UNKNOWN:
            raise InputValidationError(
                message="Unsupported or invalid document binary format (Magic bytes unrecognized).",
                provider_name="document-decoder",
            )

        # 2. MIME Consistency Check (if declared)
        if declared_mime_type:
            mime_lower = declared_mime_type.lower()
            expected_mappings = {
                ImageFormatEnum.PNG: ["image/png"],
                ImageFormatEnum.JPEG: ["image/jpeg", "image/jpg"],
                ImageFormatEnum.PDF: ["application/pdf"],
                ImageFormatEnum.TIFF: ["image/tiff"],
                ImageFormatEnum.BMP: ["image/bmp", "image/x-ms-bmp"],
                ImageFormatEnum.WEBP: ["image/webp"],
            }
            allowed_mimes = expected_mappings.get(detected_format, [])
            if allowed_mimes and not any(m in mime_lower for m in allowed_mimes):
                raise InputValidationError(
                    message=f"MIME type mismatch: Declared '{declared_mime_type}' but detected binary magic bytes for '{detected_format.value}'.",
                    provider_name="document-decoder",
                )

        metadata = {
            "format": detected_format.value,
            "sha256": doc_hash,
            "size_bytes": len(data),
            "pages": 1,
            "width": 0,
            "height": 0,
        }

        # 3. PDF Object Inspection
        if detected_format == ImageFormatEnum.PDF:
            try:
                reader = pypdf.PdfReader(io.BytesIO(data))
                page_count = len(reader.pages)
                if page_count > cls.MAX_PDF_PAGES:
                    raise InputValidationError(
                        message=f"PDF exceeds maximum page limit of {cls.MAX_PDF_PAGES} (Document contains {page_count} pages).",
                        provider_name="document-decoder",
                    )
                metadata["pages"] = page_count
                metadata["is_encrypted"] = reader.is_encrypted
            except Exception as e:
                if isinstance(e, InputValidationError):
                    raise
                raise InputValidationError(
                    message=f"Corrupt or unreadable PDF stream: {str(e)}",
                    provider_name="document-decoder",
                )
            return detected_format, metadata

        # 4. Raster Image Inspection (Pillow)
        try:
            # Set Pillow decompression bomb limits
            Image.MAX_IMAGE_PIXELS = cls.MAX_IMAGE_PIXELS
            with Image.open(io.BytesIO(data)) as img:
                width, height = img.size
                if width > cls.MAX_IMAGE_WIDTH or height > cls.MAX_IMAGE_HEIGHT:
                    raise InputValidationError(
                        message=f"Image dimensions ({width}x{height}) exceed maximum allowed bound ({cls.MAX_IMAGE_WIDTH}x{cls.MAX_IMAGE_HEIGHT}).",
                        provider_name="document-decoder",
                    )
                if (width * height) > cls.MAX_IMAGE_PIXELS:
                    raise InputValidationError(
                        message=f"Image pixel count ({width*height}) exceeds safe decompression limit ({cls.MAX_IMAGE_PIXELS}).",
                        provider_name="document-decoder",
                    )
                metadata["width"] = width
                metadata["height"] = height
                metadata["color_mode"] = img.mode
        except Exception as e:
            if isinstance(e, InputValidationError):
                raise
            raise InputValidationError(
                message=f"Failed to decode raster image: {str(e)}",
                provider_name="document-decoder",
            )

        return detected_format, metadata
