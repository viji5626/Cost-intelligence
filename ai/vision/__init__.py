"""
Vision & OCR Module (AI-15)
Provides local, air-gapped document decoding, OCR extraction,
and domain-specific automotive CAD drawing and Ideathon slip parsers.
"""

from ai.vision.document_decoder import DocumentDecoder
from ai.vision.domain_parsers import DrawingParser, IdeathonSlipParser
from ai.vision.local_ocr_engine import LocalVisionOCREngine
from ai.vision.models import (
    CapabilityStatusEnum,
    DocumentTypeEnum,
    DrawingAnnotationResult,
    DrawingTitleBlock,
    IdeathonSlipResult,
    ImageFormatEnum,
    VisionExtractionRequest,
    VisionExtractionResponse,
)
from ai.vision.ocr_engine import (
    CompositeOCRManager,
    DeterministicImageOCRBackend,
    PDFTextExtractorBackend,
    TesseractOCRBackend,
    VisionOCRProviderContract,
)

__all__ = [
    "DocumentDecoder",
    "ImageFormatEnum",
    "DocumentTypeEnum",
    "CapabilityStatusEnum",
    "DrawingTitleBlock",
    "DrawingAnnotationResult",
    "IdeathonSlipResult",
    "VisionExtractionRequest",
    "VisionExtractionResponse",
    "VisionOCRProviderContract",
    "PDFTextExtractorBackend",
    "TesseractOCRBackend",
    "DeterministicImageOCRBackend",
    "CompositeOCRManager",
    "DrawingParser",
    "IdeathonSlipParser",
    "LocalVisionOCREngine",
]
