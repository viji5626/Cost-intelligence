"""
Vision and OCR Domain Data Models (AI-15)
Defines document classifications, bounding boxes, drawing annotations,
Ideathon slip schemas, and provenance envelopes for multimodal visual assets.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ImageFormatEnum(str, Enum):
    PNG = "PNG"
    JPEG = "JPEG"
    PDF = "PDF"
    TIFF = "TIFF"
    BMP = "BMP"
    WEBP = "WEBP"
    UNKNOWN = "UNKNOWN"


class DocumentTypeEnum(str, Enum):
    ENGINEERING_DRAWING = "ENGINEERING_DRAWING"
    IDEATHON_SLIP = "IDEATHON_SLIP"
    SUPPLIER_INVOICE_BOM = "SUPPLIER_INVOICE_BOM"
    GENERAL_TEXT_DOCUMENT = "GENERAL_TEXT_DOCUMENT"
    UNKNOWN = "UNKNOWN"


class CapabilityStatusEnum(str, Enum):
    REAL_OCR = "REAL_OCR"
    REAL_VISION_MODEL = "REAL_VISION_MODEL"
    CONTRACT_ONLY = "CONTRACT_ONLY"
    NOT_VERIFIED = "NOT_VERIFIED"


class BoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    confidence: float = 1.0


class ExtractedTextRegion(BaseModel):
    text: str
    confidence: float
    bbox: Optional[BoundingBox] = None
    region_type: str = "text"  # text, title_block, dimension, note, handwritten


class DrawingTitleBlock(BaseModel):
    part_number: Optional[str] = None
    drawing_number: Optional[str] = None
    part_name: Optional[str] = None
    revision: Optional[str] = None
    material_grade: Optional[str] = None
    surface_treatment: Optional[str] = None
    drawn_by: Optional[str] = None
    approved_by: Optional[str] = None
    date: Optional[str] = None
    scale: Optional[str] = None
    general_tolerance: Optional[str] = None
    extraction_confidence: float = 0.0


class DrawingAnnotationResult(BaseModel):
    title_block: DrawingTitleBlock
    dimensions: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    weld_symbols: List[str] = Field(default_factory=list)
    tolerance_callouts: List[str] = Field(default_factory=list)
    raw_text: str = ""
    ocr_confidence: float = 0.0
    extraction_confidence: float = 0.0
    capability_classification: Dict[str, CapabilityStatusEnum] = Field(default_factory=dict)


class IdeathonSlipResult(BaseModel):
    idea_title: str = ""
    description: str = ""
    target_vehicle: Optional[str] = None
    suggested_plant: Optional[str] = None
    submitter_name: Optional[str] = None
    submitter_id: Optional[str] = None
    category: Optional[str] = None
    raw_text: str = ""
    ocr_confidence: float = 0.0
    extraction_confidence: float = 0.0
    capability_classification: Dict[str, CapabilityStatusEnum] = Field(default_factory=dict)


class VisionExtractionRequest(BaseModel):
    document_bytes: bytes
    mime_type: Optional[str] = None
    document_type: DocumentTypeEnum = DocumentTypeEnum.UNKNOWN
    model_id: Optional[str] = None
    schema_model: Optional[Any] = None
    max_pages: int = 50
    caller_identity: str = "vision-client"


class VisionExtractionResponse(BaseModel):
    request_id: str
    document_hash: str
    document_type: DocumentTypeEnum
    raw_text: str
    structured_data: Optional[Dict[str, Any]] = None
    ocr_provider: str
    vision_provider: Optional[str] = None
    model_id: Optional[str] = None
    ocr_confidence: float = 0.0
    extraction_confidence: float = 0.0
    evidence_strength: float = 0.0
    structured_validation_status: str = "SUCCESS"  # SUCCESS, VALIDATION_FAILED, SKIPPED
    provenance_snapshot: Dict[str, Any] = Field(default_factory=dict)
    execution_time_seconds: float = 0.0
    capabilities_used: Dict[str, str] = Field(default_factory=dict)
