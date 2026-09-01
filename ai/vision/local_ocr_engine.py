"""
Local Vision and OCR Engine (AI-15)
Coordinates document decoding, safety resource bounds, multi-backend OCR routing,
domain-specific automotive parsing, and AI-10 structured Pydantic validation.
"""

import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Tuple, Type
from pydantic import BaseModel, ValidationError

from ai.core.contracts import VisionOCREngineContract
from ai.grammar.structured_engine import StructuredOutputEngine
from ai.providers.exceptions import InputValidationError
from ai.vision.document_decoder import DocumentDecoder
from ai.vision.domain_parsers import DrawingParser, IdeathonSlipParser
from ai.vision.models import (
    CapabilityStatusEnum,
    DocumentTypeEnum,
    DrawingAnnotationResult,
    IdeathonSlipResult,
    ImageFormatEnum,
    VisionExtractionRequest,
    VisionExtractionResponse,
)
from ai.vision.ocr_engine import CompositeOCRManager


class LocalVisionOCREngine(VisionOCREngineContract):
    """
    Air-gapped, decoupled visual document processor.
    Implements VisionOCREngineContract with full safety and provenance attribution.
    """

    def __init__(self, ocr_manager: Optional[CompositeOCRManager] = None):
        self.ocr_manager = ocr_manager or CompositeOCRManager()

    async def extract_text(
        self,
        document_bytes: bytes,
        mime_type: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> str:
        """
        Extracts raw text content from visual document or PDF stream.
        """
        text, _, _, _ = await self.ocr_manager.extract(document_bytes, mime_type)
        return text

    async def extract_structured(
        self,
        document_bytes: bytes,
        json_schema: Dict[str, Any],
        model_id: Optional[str] = None,
        schema_model: Optional[Type[BaseModel]] = None,
    ) -> Dict[str, Any]:
        """
        Extracts structured JSON payload using OCR and AI-10 Pydantic validation.
        """
        text, conf, provider, cap_status = await self.ocr_manager.extract(document_bytes)

        # 1. Attempt JSON parsing from text
        parsed_dict: Optional[Dict[str, Any]] = None
        validation_status = "SUCCESS"

        try:
            cleaned = StructuredOutputEngine.extract_and_clean_json(text)
            parsed_dict = json.loads(cleaned)
        except Exception:
            parsed_dict = None

        # 2. Fallback to domain heuristics if direct JSON not embedded
        if parsed_dict is None:
            if "drawing" in str(json_schema).lower() or "part_number" in str(json_schema).lower():
                drawing_res = DrawingParser.parse_drawing_text(text, conf, cap_status)
                parsed_dict = drawing_res.title_block.model_dump()
            elif "ideathon" in str(json_schema).lower() or "idea_title" in str(json_schema).lower():
                slip_res = IdeathonSlipParser.parse_slip_text(text, conf, cap_status)
                parsed_dict = slip_res.model_dump()
            else:
                parsed_dict = {"extracted_text": text, "status": "RAW_TEXT_ONLY"}

        # 3. Pydantic validation if schema_model is provided (AI-10 integration)
        if schema_model and issubclass(schema_model, BaseModel):
            try:
                validated_obj = schema_model.model_validate(parsed_dict)
                parsed_dict = validated_obj.model_dump()
                validation_status = "VALIDATED"
            except ValidationError as ve:
                validation_status = "VALIDATION_FAILED"
                parsed_dict["_validation_errors"] = [str(e) for e in ve.errors()]

        return {
            "status": validation_status,
            "data": parsed_dict,
            "ocr_confidence": conf,
            "provider": provider,
        }

    async def process_document(
        self,
        request: VisionExtractionRequest,
    ) -> VisionExtractionResponse:
        """
        Executes full visual extraction pipeline with precision telemetry and provenance.
        """
        t0 = time.perf_counter()

        # 1. Decoding & Safety Validation
        format_enum, meta = DocumentDecoder.validate_and_decode(
            request.document_bytes,
            request.mime_type,
        )
        t_decode = time.perf_counter()

        # 2. OCR Text Extraction
        raw_text, ocr_conf, ocr_provider, ocr_status = await self.ocr_manager.extract(
            request.document_bytes,
            request.mime_type,
        )
        t_ocr = time.perf_counter()

        # 3. Domain Parsing / Structured Extraction
        structured_data: Optional[Dict[str, Any]] = None
        extraction_conf = ocr_conf
        validation_status = "SUCCESS"
        capabilities_used: Dict[str, str] = {
            "OCR_ENGINE": ocr_provider,
            "OCR_STATUS": ocr_status.value,
        }

        if request.document_type == DocumentTypeEnum.ENGINEERING_DRAWING:
            drawing_res = DrawingParser.parse_drawing_text(raw_text, ocr_conf, ocr_status)
            structured_data = drawing_res.model_dump()
            extraction_conf = drawing_res.extraction_confidence
            for k, v in drawing_res.capability_classification.items():
                capabilities_used[k] = v.value

        elif request.document_type == DocumentTypeEnum.IDEATHON_SLIP:
            slip_res = IdeathonSlipParser.parse_slip_text(raw_text, ocr_conf, ocr_status)
            structured_data = slip_res.model_dump()
            extraction_conf = slip_res.extraction_confidence
            for k, v in slip_res.capability_classification.items():
                capabilities_used[k] = v.value

        elif request.schema_model:
            struct_res = await self.extract_structured(
                request.document_bytes,
                json_schema=request.schema_model.model_json_schema() if hasattr(request.schema_model, "model_json_schema") else {},
                model_id=request.model_id,
                schema_model=request.schema_model if isinstance(request.schema_model, type) and issubclass(request.schema_model, BaseModel) else None,
            )
            structured_data = struct_res.get("data")
            validation_status = struct_res.get("status", "SUCCESS")

        t_end = time.perf_counter()

        # 4. Separate Evidence Strength from OCR Confidence
        # Evidence strength accounts for both OCR confidence and schema completeness
        evidence_strength = round(min(1.0, (ocr_conf * 0.5) + (extraction_conf * 0.5)), 4)

        doc_hash = meta.get("sha256", hashlib.sha256(request.document_bytes).hexdigest())

        provenance_snapshot = {
            "request_id": f"vis-{doc_hash[:12]}",
            "document_hash": doc_hash,
            "document_format": format_enum.value,
            "size_bytes": len(request.document_bytes),
            "pages": meta.get("pages", 1),
            "ocr_provider": ocr_provider,
            "ocr_capability_status": ocr_status.value,
            "decode_latency_ms": round((t_decode - t0) * 1000.0, 2),
            "ocr_latency_ms": round((t_ocr - t_decode) * 1000.0, 2),
            "parse_latency_ms": round((t_end - t_ocr) * 1000.0, 2),
            "total_latency_ms": round((t_end - t0) * 1000.0, 2),
        }

        return VisionExtractionResponse(
            request_id=provenance_snapshot["request_id"],
            document_hash=doc_hash,
            document_type=request.document_type,
            raw_text=raw_text,
            structured_data=structured_data,
            ocr_provider=ocr_provider,
            vision_provider=None,  # Real Vision Model absent unless loaded in AI-02
            model_id=request.model_id,
            ocr_confidence=ocr_conf,
            extraction_confidence=extraction_conf,
            evidence_strength=evidence_strength,
            structured_validation_status=validation_status,
            provenance_snapshot=provenance_snapshot,
            execution_time_seconds=round(t_end - t0, 4),
            capabilities_used=capabilities_used,
        )
