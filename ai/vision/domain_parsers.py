"""
Domain-Specific Automotive Visual Document Parsers (AI-15)
Parses CAD engineering drawing annotations, Ideathon paper slips, and supplier invoice BOMs.
Strictly separates verified extraction capabilities from unverified visual detectors.
"""

import re
from typing import Any, Dict, List, Optional
from ai.vision.models import (
    CapabilityStatusEnum,
    DrawingAnnotationResult,
    DrawingTitleBlock,
    IdeathonSlipResult,
)


class DrawingParser:
    """
    Automotive CAD Drawing Parser.
    Extracts title block metadata, engineering dimensions, and general notes.
    """

    PART_NUMBER_REGEX = re.compile(r"\b\d{5}-[A-Za-z0-9]{3,5}-[A-Za-z0-9]{3,5}\b", re.IGNORECASE)
    DRAWING_NO_REGEX = re.compile(r"\b(?:DWG|DRAWING|PART\s*NO)[\s:\#\.\-]+([A-Za-z0-9\-_]{5,20})\b", re.IGNORECASE)
    REVISION_REGEX = re.compile(r"\b(?:REV|REVISION|VERSION)[\s:\#\.\-]+([A-Za-z0-9]{1,4})\b", re.IGNORECASE)
    MATERIAL_REGEX = re.compile(
        r"\b(ADC12|AISI\s*\d{4}|EN\s*\d+[A-Za-z]?|SS\s*\d{3}|AL\s*\d{4}|C45|EN8D|EN24|SAE\s*\d{4}|ALUMINUM|CAST\s*IRON|STRUCTURAL\s*STEEL)\b",
        re.IGNORECASE,
    )
    SURFACE_REGEX = re.compile(
        r"\b(ANODIZED|ZINC\s*PLATED|POWDER\s*COATED|NITRIDED|PASSIVATED|HARD\s*CHROME|BLACK\s*OXIDE|PHOSPHATED)\b",
        re.IGNORECASE,
    )
    DIMENSION_REGEX = re.compile(r"\b(?:Ø\s*)?\d+(?:\.\d+)?\s*(?:mm|deg|°|±\s*\d+(?:\.\d+)?)\b", re.IGNORECASE)
    TOLERANCE_REGEX = re.compile(r"\b(?:ISO\s*2768-[a-zA-Z]+|±\s*\d+\.\d+|GD&T\s*[A-Za-z0-9\-_]+)\b", re.IGNORECASE)

    @classmethod
    def parse_drawing_text(
        cls,
        text: str,
        ocr_confidence: float = 0.85,
        ocr_status: CapabilityStatusEnum = CapabilityStatusEnum.REAL_OCR,
    ) -> DrawingAnnotationResult:
        """Parses extracted drawing OCR text into structured engineering attributes."""
        # 1. Title Block Extraction
        part_no_match = cls.PART_NUMBER_REGEX.search(text)
        part_no = part_no_match.group(0).upper() if part_no_match else None

        dwg_match = cls.DRAWING_NO_REGEX.search(text)
        dwg_no = dwg_match.group(1).upper() if dwg_match else part_no

        rev_match = cls.REVISION_REGEX.search(text)
        rev = rev_match.group(1).upper() if rev_match else "A"

        mat_match = cls.MATERIAL_REGEX.search(text)
        mat = mat_match.group(0).upper() if mat_match else None

        surf_match = cls.SURFACE_REGEX.search(text)
        surf = surf_match.group(0).upper() if surf_match else None

        tol_match = cls.TOLERANCE_REGEX.search(text)
        tol = tol_match.group(0) if tol_match else "ISO 2768-m"

        # Compute title block extraction confidence
        found_fields = sum(1 for f in [part_no, dwg_no, rev, mat, surf] if f is not None)
        extraction_conf = round(min(1.0, 0.4 + (found_fields * 0.15)), 2)

        title_block = DrawingTitleBlock(
            part_number=part_no,
            drawing_number=dwg_no,
            revision=rev,
            material_grade=mat,
            surface_treatment=surf,
            general_tolerance=tol,
            extraction_confidence=extraction_conf,
        )

        # 2. Dimensions & Notes
        dimensions = list(set(cls.DIMENSION_REGEX.findall(text)))
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        notes = [l for l in lines if any(k in l.lower() for k in ["note", "all dimensions", "deburr", "chamfer", "torque"])]

        # 3. Explicit Capability Classification Breakdown
        cap_breakdown = {
            "TITLE_BLOCK_OCR": ocr_status,
            "TEXT_ANNOTATION_EXTRACTION": ocr_status,
            "DIMENSION_EXTRACTION": ocr_status,
            "SYMBOL_DETECTION": CapabilityStatusEnum.NOT_VERIFIED,
            "GDT_INTERPRETATION": CapabilityStatusEnum.NOT_VERIFIED,
            "WELD_SYMBOL_INTERPRETATION": CapabilityStatusEnum.NOT_VERIFIED,
        }

        return DrawingAnnotationResult(
            title_block=title_block,
            dimensions=dimensions,
            notes=notes,
            weld_symbols=[],  # Explicitly empty: weld symbol detector not verified
            tolerance_callouts=[tol] if tol else [],
            raw_text=text,
            ocr_confidence=ocr_confidence,
            extraction_confidence=extraction_conf,
            capability_classification=cap_breakdown,
        )


class IdeathonSlipParser:
    """
    Scanned Ideathon Paper Slip Parser.
    Extracts submitter, target vehicle model, suggested plant, and core idea description.
    """

    PLANTS = ["Haridwar", "Dharuhera", "Gurgaon", "Neemrana", "Vadodara", "Chittoor"]
    VEHICLES = ["Splendor", "HF Deluxe", "Passion", "Glamour", "Xpulse", "Destini", "Pleasure", "Vida V1"]
    EMP_REGEX = re.compile(r"\b(?:EMP|HM|ID)[\s:\#\.\-]+([A-Za-z0-9]{4,10})\b", re.IGNORECASE)

    @classmethod
    def parse_slip_text(
        cls,
        text: str,
        ocr_confidence: float = 0.85,
        ocr_status: CapabilityStatusEnum = CapabilityStatusEnum.REAL_OCR,
    ) -> IdeathonSlipResult:
        """Parses extracted Ideathon slip text into normalized submission entities."""
        text_lower = text.lower()

        # Plant Detection
        matched_plant = None
        for p in cls.PLANTS:
            if p.lower() in text_lower:
                matched_plant = p
                break

        # Vehicle Detection
        matched_vehicle = None
        for v in cls.VEHICLES:
            if v.lower() in text_lower:
                matched_vehicle = v
                break

        # Employee / Submitter ID
        emp_match = cls.EMP_REGEX.search(text)
        submitter_id = emp_match.group(1).upper() if emp_match else None

        # Title and Description extraction
        lines = [l.strip() for l in text.splitlines() if l.strip() and not l.startswith("---")]
        title = lines[0] if lines else "Unlabeled Improvement Idea"
        description = "\n".join(lines[1:]) if len(lines) > 1 else text

        found_entities = sum(1 for e in [matched_plant, matched_vehicle, submitter_id] if e is not None)
        extraction_conf = round(min(1.0, 0.5 + (found_entities * 0.15)), 2)

        # Explicitly separate PRINTED_OCR vs HANDWRITING_OCR
        cap_breakdown = {
            "PRINTED_OCR": ocr_status,
            "HANDWRITING_OCR": CapabilityStatusEnum.NOT_VERIFIED,
            "VISION_STRUCTURED_EXTRACTION": CapabilityStatusEnum.CONTRACT_ONLY,
        }

        return IdeathonSlipResult(
            idea_title=title[:120],
            description=description,
            target_vehicle=matched_vehicle,
            suggested_plant=matched_plant,
            submitter_id=submitter_id,
            raw_text=text,
            ocr_confidence=ocr_confidence,
            extraction_confidence=extraction_conf,
            capability_classification=cap_breakdown,
        )
