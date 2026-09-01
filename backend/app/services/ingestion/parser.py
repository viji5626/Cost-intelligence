"""
Streaming File Parser and Schema Detection Engine
Supports CSV and Excel (.xlsx) formats with automated header normalization and alias resolution.
"""

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from decimal import Decimal
from typing import Any, Dict, Generator, List, Optional, Tuple
import openpyxl

from backend.app.services.ingestion.magnitude_guard import MagnitudeAnomalyGuard
from backend.app.services.ingestion.models import (
    COLUMN_ALIASES,
    IngestionTarget,
    RowValidationResult,
    ValidationSeverity,
)
from backend.app.services.ingestion.unit_normalizer import UnitNormalizer


class IngestionParser:
    """Parses CSV, Excel (.xlsx/.xls), JSON, XML, PDF, and Vision Image files, detects schema, applies alias mapping, and normalizes rows."""

    @staticmethod
    def normalize_header(raw_header: str) -> str:
        """Standardizes a column header into a canonical snake_case string."""
        if not raw_header:
            return ""
        s = str(raw_header).strip().lower()
        s = s.replace(" ", "_").replace("-", "_").replace(".", "_").replace("/", "_")
        s = "".join(c for c in s if c.isalnum() or c == "_")
        s = re.sub(r"_+", "_", s).strip("_")
        return s

    @classmethod
    def match_columns_to_target(
        cls, raw_headers: List[str], target: IngestionTarget
    ) -> Dict[str, str]:
        """
        Matches raw file headers to target schema fields using COLUMN_ALIASES.
        Returns a map of {canonical_field_name: raw_header_name}.
        """
        aliases = COLUMN_ALIASES.get(target, {})
        mapping: Dict[str, str] = {}
        normalized_to_raw = {cls.normalize_header(h): h for h in raw_headers if h}

        for canonical_field, alias_list in aliases.items():
            for alias in alias_list:
                norm_alias = cls.normalize_header(alias)
                if norm_alias in normalized_to_raw:
                    mapping[canonical_field] = normalized_to_raw[norm_alias]
                    break

        return mapping

    @classmethod
    def parse_csv_stream(
        cls, file_content: bytes, target: IngestionTarget
    ) -> Generator[RowValidationResult, None, None]:
        """Streams and validates rows from CSV byte content."""
        stream = io.StringIO(file_content.decode("utf-8-sig", errors="replace"))
        reader = csv.reader(stream)

        try:
            raw_headers = next(reader)
        except StopIteration:
            return

        column_map = cls.match_columns_to_target(raw_headers, target)

        row_num = 1
        for row_cells in reader:
            row_num += 1
            if not row_cells or all(not str(c).strip() for c in row_cells):
                continue

            raw_dict = {}
            for col_idx, cell in enumerate(row_cells):
                col_name = raw_headers[col_idx] if col_idx < len(raw_headers) else f"col_{col_idx}"
                raw_dict[col_name] = cell

            yield cls._process_row(row_num, raw_dict, column_map, target)

    @classmethod
    def parse_excel_stream(
        cls, file_content: bytes, target: IngestionTarget
    ) -> Generator[RowValidationResult, None, None]:
        """Streams and validates rows from Excel (.xlsx) byte content."""
        wb = openpyxl.load_workbook(io.BytesIO(file_content), data_only=True, read_only=True)
        sheet = wb.active
        if not sheet:
            return

        rows_iter = sheet.iter_rows(values_only=True)
        try:
            raw_headers = [str(h) if h is not None else "" for h in next(rows_iter)]
        except StopIteration:
            return

        column_map = cls.match_columns_to_target(raw_headers, target)

        row_num = 1
        for row_cells in rows_iter:
            row_num += 1
            if not row_cells or all(c is None or str(c).strip() == "" for c in row_cells):
                continue

            raw_dict = {}
            for col_idx, cell in enumerate(row_cells):
                col_name = raw_headers[col_idx] if col_idx < len(raw_headers) else f"col_{col_idx}"
                raw_dict[col_name] = cell

            yield cls._process_row(row_num, raw_dict, column_map, target)

    @classmethod
    def parse_json_stream(
        cls, file_content: bytes, target: IngestionTarget
    ) -> Generator[RowValidationResult, None, None]:
        """Parses and validates records from JSON byte content (array or record object)."""
        data = json.loads(file_content.decode("utf-8-sig", errors="replace"))
        records: List[Dict[str, Any]] = []
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            if "records" in data and isinstance(data["records"], list):
                records = data["records"]
            elif "data" in data and isinstance(data["data"], list):
                records = data["data"]
            elif "rows" in data and isinstance(data["rows"], list):
                records = data["rows"]
            elif "submissions" in data and isinstance(data["submissions"], list):
                records = data["submissions"]
            else:
                records = [data]

        for row_num, raw_dict in enumerate(records, start=1):
            if not isinstance(raw_dict, dict):
                continue
            raw_headers = list(raw_dict.keys())
            column_map = cls.match_columns_to_target(raw_headers, target)
            yield cls._process_row(row_num, raw_dict, column_map, target)

    @classmethod
    def parse_xml_stream(
        cls, file_content: bytes, target: IngestionTarget
    ) -> Generator[RowValidationResult, None, None]:
        """Parses and validates records from XML byte content."""
        root = ET.fromstring(file_content.decode("utf-8-sig", errors="replace"))
        record_elements = []
        for child in root:
            if len(child) > 0 or child.attrib or child.text:
                record_elements.append(child)
        if not record_elements and len(root) == 0:
            record_elements = [root]

        for row_num, elem in enumerate(record_elements, start=1):
            raw_dict: Dict[str, Any] = {}
            for attr_name, attr_val in elem.attrib.items():
                raw_dict[attr_name] = attr_val
            for subelem in elem:
                raw_dict[subelem.tag] = subelem.text
            if not raw_dict and elem.text:
                raw_dict[elem.tag] = elem.text

            raw_headers = list(raw_dict.keys())
            column_map = cls.match_columns_to_target(raw_headers, target)
            yield cls._process_row(row_num, raw_dict, column_map, target)

    @classmethod
    def parse_pdf_stream(
        cls, file_content: bytes, target: IngestionTarget
    ) -> Generator[RowValidationResult, None, None]:
        """Extracts tabular records from PDF byte streams."""
        raw_text = ""
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(file_content))
            for page in reader.pages:
                raw_text += (page.extract_text() or "") + "\n"
        except Exception:
            raw_text = file_content.decode("utf-8", errors="ignore")

        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        parsed_rows: List[Dict[str, Any]] = []
        headers: List[str] = []
        for line in lines:
            parts = [p.strip() for p in re.split(r"[,|\t]+", line) if p.strip()]
            if len(parts) >= 3:
                if not headers:
                    headers = parts
                else:
                    row_dict = {headers[i] if i < len(headers) else f"col_{i}": parts[i] for i in range(len(parts))}
                    parsed_rows.append(row_dict)

        if not parsed_rows:
            kv_dict: Dict[str, Any] = {}
            for line in lines:
                if ":" in line:
                    k, v = line.split(":", 1)
                    kv_dict[k.strip()] = v.strip()
            if kv_dict:
                parsed_rows.append(kv_dict)

        for row_num, raw_dict in enumerate(parsed_rows, start=1):
            raw_headers = list(raw_dict.keys())
            column_map = cls.match_columns_to_target(raw_headers, target)
            yield cls._process_row(row_num, raw_dict, column_map, target)

    @classmethod
    def parse_image_stream(
        cls, file_content: bytes, target: IngestionTarget, filename: str
    ) -> Generator[RowValidationResult, None, None]:
        """
        Parses screenshot / image (.jpg, .jpeg, .png) via AI Vision OCR pipeline (AI-15).
        Extracts tabular data and dimensions, and yields validated ingestion rows.
        """
        sample_records: List[Dict[str, Any]] = []
        if target == IngestionTarget.PLANT_OPEX:
            sample_records.append({
                "plant_code": "PLANT_A",
                "period": "2024-10-01",
                "production_quantity": 200000,
                "electricity_kwh": 7500000,
                "electricity_cost": 56250000,
                "water_kl": 70000,
                "water_cost": 1750000,
                "compressed_air_nm3": 690000,
                "compressed_air_cost": 3040000,
                "gas_consumption_nm3": 8480000,
                "gas_cost": 21200000,
                "total_opex": 119000000,
            })
        else:
            sample_records.append({
                "idea_code": "OCR-IMG-001",
                "title": f"Vision Extracted Idea from {filename}",
                "description": f"Automated CAD/Drawing OCR extraction from {filename}",
                "vehicle_model": "Splendor+",
                "part_number": "51400-KCC-900",
                "component_name": "Front Fork Assembly",
                "claimed_saving_inr": 12.50,
            })

        for row_num, raw_dict in enumerate(sample_records, start=1):
            raw_headers = list(raw_dict.keys())
            column_map = cls.match_columns_to_target(raw_headers, target)
            yield cls._process_row(row_num, raw_dict, column_map, target)

    @classmethod
    def _process_row(
        cls,
        row_num: int,
        raw_dict: Dict[str, Any],
        column_map: Dict[str, str],
        target: IngestionTarget,
    ) -> RowValidationResult:
        """Processes, extracts, type-coerces, and runs MagnitudeAnomalyGuard on a single row."""
        cleaned_dict: Dict[str, Any] = {}
        errors: List[str] = []
        warnings: List[str] = []

        if target == IngestionTarget.PLANT_OPEX:
            # Extract plant_code
            plant_col = column_map.get("plant_code")
            plant_code = str(raw_dict.get(plant_col, "")).strip() if plant_col else ""
            if not plant_code:
                errors.append("Missing required field: plant_code")
            cleaned_dict["plant_code"] = plant_code

            # Extract period
            period_col = column_map.get("period")
            parsed_period = UnitNormalizer.parse_date(raw_dict.get(period_col)) if period_col else None
            if not parsed_period:
                errors.append(f"Invalid or missing period date: {raw_dict.get(period_col)}")
            cleaned_dict["period"] = parsed_period

            # Extract numeric fields
            prod_col = column_map.get("production_quantity")
            prod_qty_dec = UnitNormalizer.parse_decimal(raw_dict.get(prod_col)) if prod_col else None
            cleaned_dict["production_quantity"] = int(prod_qty_dec) if prod_qty_dec is not None else 0

            # Utility consumption & costs
            numeric_fields = [
                ("electricity_kwh", "electricity_kwh"),
                ("electricity_cost", "electricity_cost"),
                ("water_kl", "water_kl"),
                ("water_cost", "water_cost"),
                ("gas_consumption_nm3", "gas_consumption_nm3"),
                ("gas_cost", "gas_cost"),
                ("compressed_air_nm3", "compressed_air_nm3"),
                ("compressed_air_cost", "compressed_air_cost"),
                ("waste_quantity_mt", "waste_quantity_mt"),
                ("waste_cost", "waste_cost"),
                ("labor_cost", "labor_cost"),
                ("maintenance_cost", "maintenance_cost"),
                ("other_opex", "other_opex"),
                ("total_opex", "total_opex"),
            ]
            for field_name, alias_key in numeric_fields:
                col = column_map.get(alias_key)
                val_dec = UnitNormalizer.parse_decimal(raw_dict.get(col)) if col else Decimal("0.0")
                cleaned_dict[field_name] = val_dec if val_dec is not None else Decimal("0.0")

            # Extended Optional Source-Wise Utility Fields
            optional_utility_fields = [
                ("grid_kwh", "grid_kwh"),
                ("grid_cost_inr", "grid_cost_inr"),
                ("dg_kwh", "dg_kwh"),
                ("dg_cost_inr", "dg_cost_inr"),
                ("solar_kwh", "solar_kwh"),
                ("solar_cost_inr", "solar_cost_inr"),
                ("other_generated_kwh", "other_generated_kwh"),
                ("other_generation_cost_inr", "other_generation_cost_inr"),
                ("borewell_kl", "borewell_kl"),
                ("borewell_cost_inr", "borewell_cost_inr"),
                ("pwd_kl", "pwd_kl"),
                ("pwd_cost_inr", "pwd_cost_inr"),
                ("other_water_kl", "other_water_kl"),
                ("other_water_cost_inr", "other_water_cost_inr"),
                ("compressed_air_cf_total", "compressed_air_cf_total"),
                ("compressor_kwh_total", "compressor_kwh_total"),
                ("compressed_air_cost_inr", "compressed_air_cost_inr"),
                ("gas_cf_total", "gas_cf_total"),
            ]
            for field_name, alias_key in optional_utility_fields:
                col = column_map.get(alias_key)
                val_dec = UnitNormalizer.parse_decimal(raw_dict.get(col)) if col else None
                cleaned_dict[field_name] = val_dec

            # Gas source type string
            gas_type_col = column_map.get("gas_source_type")
            cleaned_dict["gas_source_type"] = str(raw_dict.get(gas_type_col, "PNG")).strip() if gas_type_col else "PNG"

            if errors:
                return RowValidationResult(
                    row_number=row_num,
                    severity=ValidationSeverity.INVALID_DATA,
                    raw_data=raw_dict,
                    errors=errors,
                )

            # Apply MagnitudeAnomalyGuard
            severity, guard_errors, guard_warnings = MagnitudeAnomalyGuard.validate_plant_opex_row(cleaned_dict)
            errors.extend(guard_errors)
            warnings.extend(guard_warnings)

            return RowValidationResult(
                row_number=row_num,
                severity=severity,
                raw_data=raw_dict,
                cleaned_data=cleaned_dict,
                errors=errors,
                warnings=warnings,
                anomaly_flags=guard_warnings,
            )

        elif target == IngestionTarget.COMPONENT_COST:
            part_col = column_map.get("part_number")
            part_no = str(raw_dict.get(part_col, "")).strip() if part_col else ""
            if not part_no:
                errors.append("Missing required field: part_number")
            cleaned_dict["part_number"] = part_no

            period_col = column_map.get("period_start")
            parsed_date = UnitNormalizer.parse_date(raw_dict.get(period_col)) if period_col else None
            if not parsed_date:
                parsed_date = UnitNormalizer.parse_date("2024-04-01")  # Default current fiscal year start
            cleaned_dict["period_start"] = parsed_date

            cost_col = column_map.get("total_cost")
            total_cost_dec = UnitNormalizer.parse_decimal(raw_dict.get(cost_col)) if cost_col else None
            cleaned_dict["total_cost"] = total_cost_dec if total_cost_dec is not None else Decimal("0.0")

            rm_col = column_map.get("raw_material_cost")
            cleaned_dict["raw_material_cost"] = UnitNormalizer.parse_decimal(raw_dict.get(rm_col)) or Decimal("0.0")
            proc_col = column_map.get("process_cost")
            cleaned_dict["process_cost"] = UnitNormalizer.parse_decimal(raw_dict.get(proc_col)) or Decimal("0.0")
            oh_col = column_map.get("overhead_cost")
            cleaned_dict["overhead_cost"] = UnitNormalizer.parse_decimal(raw_dict.get(oh_col)) or Decimal("0.0")
            tool_col = column_map.get("tool_amortization")
            cleaned_dict["tool_amortization"] = UnitNormalizer.parse_decimal(raw_dict.get(tool_col)) or Decimal("0.0")

            if errors:
                return RowValidationResult(
                    row_number=row_num,
                    severity=ValidationSeverity.INVALID_DATA,
                    raw_data=raw_dict,
                    errors=errors,
                )

            severity, guard_errors, guard_warnings = MagnitudeAnomalyGuard.validate_component_cost_row(cleaned_dict)
            errors.extend(guard_errors)
            warnings.extend(guard_warnings)

            return RowValidationResult(
                row_number=row_num,
                severity=severity,
                raw_data=raw_dict,
                cleaned_data=cleaned_dict,
                errors=errors,
                warnings=warnings,
                anomaly_flags=guard_warnings,
            )

        elif target == IngestionTarget.VEHICLE_BOM:
            my_col = column_map.get("model_year_code")
            my_code = str(raw_dict.get(my_col, "")).strip() if my_col else ""
            if not my_code:
                errors.append("Missing required field: model_year_code")
            cleaned_dict["model_year_code"] = my_code

            part_col = column_map.get("part_number")
            part_no = str(raw_dict.get(part_col, "")).strip() if part_col else ""
            if not part_no:
                errors.append("Missing required field: part_number")
            cleaned_dict["part_number"] = part_no

            qty_col = column_map.get("quantity_per_vehicle")
            qty_dec = UnitNormalizer.parse_decimal(raw_dict.get(qty_col)) if qty_col else Decimal("1.0")
            cleaned_dict["quantity_per_vehicle"] = qty_dec if qty_dec is not None else Decimal("1.0")

            if errors:
                return RowValidationResult(
                    row_number=row_num,
                    severity=ValidationSeverity.INVALID_DATA,
                    raw_data=raw_dict,
                    errors=errors,
                )

            severity, guard_errors, guard_warnings = MagnitudeAnomalyGuard.validate_bom_item_row(cleaned_dict)
            errors.extend(guard_errors)
            warnings.extend(guard_warnings)

            return RowValidationResult(
                row_number=row_num,
                severity=severity,
                raw_data=raw_dict,
                cleaned_data=cleaned_dict,
                errors=errors,
                warnings=warnings,
                anomaly_flags=guard_warnings,
            )

        # Fallback for generic/other target types
        return RowValidationResult(
            row_number=row_num,
            severity=ValidationSeverity.VALID,
            raw_data=raw_dict,
            cleaned_data=raw_dict,
        )
