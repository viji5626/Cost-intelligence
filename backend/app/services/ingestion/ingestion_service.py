"""
Master Ingestion Service
Coordinates temporary staging, parsing, validation, transactional commit/rollback,
automatic staging purge, duplicate handling, and audit trail logging.
"""

import hashlib
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import audit_logger, logger
from backend.app.services.ingestion.models import (
    IngestionBatchSummary,
    IngestionTarget,
    RowValidationResult,
    ValidationSeverity,
)
from backend.app.services.ingestion.parser import IngestionParser
from database.models.audit import AuditLog
from database.models.part_bom import BomItem, ComponentCost, Part
from database.models.plant_opex import OpexRecord, Plant
from database.models.vehicle_hierarchy import ModelYear


class IngestionService:
    """Enterprise file ingestion orchestrator with transactional safety."""

    @classmethod
    async def process_file_bytes(
        cls,
        session: AsyncSession,
        file_bytes: bytes,
        filename: str,
        target: IngestionTarget,
        user_id: Optional[str] = None,
        dry_run: bool = False,
        allow_unusual_data: bool = True,
    ) -> IngestionBatchSummary:
        """
        Main entry point for processing an uploaded file.
        Computes SHA-256 hash, parses, validates, and transactionally commits records.
        """
        start_time = time.time()
        ingestion_id = f"ing-{uuid.uuid4().hex[:12]}"
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        logger.info(f"Starting ingestion [{ingestion_id}] for file '{filename}' target={target.value} (dry_run={dry_run})")

        # 1. Parse streaming generator based on file type
        fn_lower = filename.lower()
        if fn_lower.endswith(".csv"):
            row_generator = IngestionParser.parse_csv_stream(file_bytes, target)
        elif fn_lower.endswith((".xlsx", ".xls")):
            row_generator = IngestionParser.parse_excel_stream(file_bytes, target)
        elif fn_lower.endswith(".json"):
            row_generator = IngestionParser.parse_json_stream(file_bytes, target)
        elif fn_lower.endswith(".xml"):
            row_generator = IngestionParser.parse_xml_stream(file_bytes, target)
        elif fn_lower.endswith(".pdf"):
            row_generator = IngestionParser.parse_pdf_stream(file_bytes, target)
        elif fn_lower.endswith((".png", ".jpg", ".jpeg")):
            row_generator = IngestionParser.parse_image_stream(file_bytes, target, filename)
        else:
            raise ValueError(
                f"Unsupported file format for '{filename}'. Supported: .csv, .xlsx, .xls, .json, .xml, .pdf, .png, .jpg, .jpeg"
            )

        total_rows = 0
        valid_rows = 0
        unusual_rows = 0
        rejected_rows = 0
        rejected_details: List[RowValidationResult] = []
        unusual_details: List[RowValidationResult] = []
        rows_to_insert: List[Dict[str, Any]] = []

        # 2. Iterate and classify rows
        for row_result in row_generator:
            total_rows += 1
            if row_result.severity == ValidationSeverity.INVALID_DATA:
                rejected_rows += 1
                rejected_details.append(row_result)
            elif row_result.severity == ValidationSeverity.UNUSUAL_VALID_DATA:
                unusual_rows += 1
                unusual_details.append(row_result)
                if allow_unusual_data and row_result.cleaned_data:
                    rows_to_insert.append({**row_result.cleaned_data, "_is_anomaly": True})
            else:
                valid_rows += 1
                if row_result.cleaned_data:
                    rows_to_insert.append({**row_result.cleaned_data, "_is_anomaly": False})

        # 3. Database Insertion (if not dry-run and valid rows exist)
        if not dry_run and rows_to_insert:
            try:
                await cls._persist_records(session, target, rows_to_insert)
                await session.commit()
            except Exception as exc:
                await session.rollback()
                logger.error(f"Ingestion [{ingestion_id}] database transaction failed: {exc}", exc_info=True)
                raise RuntimeError(f"Database insertion failed: {exc}") from exc

        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Determine batch status
        if rejected_rows == 0 and unusual_rows == 0:
            status = "COMPLETED"
        elif rejected_rows == 0 and unusual_rows > 0:
            status = "COMPLETED_WITH_WARNINGS"
        elif valid_rows > 0:
            status = "PARTIALLY_COMPLETED"
        else:
            status = "FAILED_REJECTED"

        summary = IngestionBatchSummary(
            ingestion_id=ingestion_id,
            target=target,
            filename=filename,
            file_hash=file_hash,
            total_rows=total_rows,
            valid_rows=valid_rows,
            unusual_rows=unusual_rows,
            rejected_rows=rejected_rows,
            duration_ms=duration_ms,
            status=status,
            rejected_details=rejected_details,
            unusual_details=unusual_details,
        )

        # 4. Audit Trail Recording
        if not dry_run:
            audit_entry = AuditLog(
                user_id=user_id,
                action="INGESTION_BATCH",
                entity_type=target.value,
                entity_id=ingestion_id,
                workflow_id=ingestion_id,
                decision=status,
                evidence_hash=file_hash,
                metadata_json={
                    "filename": filename,
                    "total_rows": total_rows,
                    "valid_rows": valid_rows,
                    "unusual_rows": unusual_rows,
                    "rejected_rows": rejected_rows,
                    "duration_ms": duration_ms,
                },
            )
            session.add(audit_entry)
            await session.commit()

        logger.info(
            f"Ingestion [{ingestion_id}] finished: total={total_rows}, valid={valid_rows}, "
            f"unusual={unusual_rows}, rejected={rejected_rows} in {duration_ms}ms"
        )
        return summary

    @classmethod
    async def _persist_records(
        cls,
        session: AsyncSession,
        target: IngestionTarget,
        rows: List[Dict[str, Any]],
    ) -> None:
        """Persists validated rows into their respective PostgreSQL tables."""
        if target == IngestionTarget.PLANT_OPEX:
            # Prefetch plants cache by code
            plants_res = await session.execute(select(Plant))
            plants_map = {p.plant_code.upper(): p.id for p in plants_res.scalars().all()}

            for r in rows:
                p_code = r.get("plant_code", "").upper()
                plant_id = plants_map.get(p_code)
                if not plant_id:
                    # Create plant if not exists in master for robust ingestion
                    new_plant = Plant(
                        plant_code=p_code,
                        name=f"Plant {p_code}",
                        location="Automated Ingestion",
                        state="Unknown",
                    )
                    session.add(new_plant)
                    await session.flush()
                    plant_id = new_plant.id
                    plants_map[p_code] = plant_id

                opex_rec = OpexRecord(
                    plant_id=plant_id,
                    period=r["period"],
                    production_quantity=r["production_quantity"],
                    electricity_kwh=r["electricity_kwh"],
                    electricity_cost=r["electricity_cost"],
                    grid_kwh=r.get("grid_kwh"),
                    grid_cost_inr=r.get("grid_cost_inr"),
                    dg_kwh=r.get("dg_kwh"),
                    dg_cost_inr=r.get("dg_cost_inr"),
                    solar_kwh=r.get("solar_kwh"),
                    solar_cost_inr=r.get("solar_cost_inr"),
                    other_generated_kwh=r.get("other_generated_kwh"),
                    other_generation_cost_inr=r.get("other_generation_cost_inr"),
                    water_kl=r["water_kl"],
                    water_cost=r["water_cost"],
                    borewell_kl=r.get("borewell_kl"),
                    borewell_cost_inr=r.get("borewell_cost_inr"),
                    pwd_kl=r.get("pwd_kl"),
                    pwd_cost_inr=r.get("pwd_cost_inr"),
                    other_water_kl=r.get("other_water_kl"),
                    other_water_cost_inr=r.get("other_water_cost_inr"),
                    compressed_air_nm3=r["compressed_air_nm3"],
                    compressed_air_cost=r["compressed_air_cost"],
                    compressed_air_cf_total=r.get("compressed_air_cf_total"),
                    compressor_kwh_total=r.get("compressor_kwh_total"),
                    compressed_air_cost_allocated=r.get("compressed_air_cost_inr"),
                    is_compressor_power_embedded=r.get("is_compressor_power_embedded", True),
                    gas_consumption_nm3=r["gas_consumption_nm3"],
                    gas_cost=r["gas_cost"],
                    gas_cf_total=r.get("gas_cf_total"),
                    gas_source_type=r.get("gas_source_type", "PNG"),
                    waste_quantity_mt=r["waste_quantity_mt"],
                    waste_cost=r["waste_cost"],
                    labor_cost=r["labor_cost"],
                    maintenance_cost=r["maintenance_cost"],
                    other_opex=r["other_opex"],
                    total_opex=r["total_opex"],
                    is_anomaly=r.get("_is_anomaly", False),
                    validation_status="VERIFIED" if not r.get("_is_anomaly") else "UNUSUAL_WARNING",
                )
                session.add(opex_rec)

        elif target == IngestionTarget.COMPONENT_COST:
            # Prefetch parts cache
            parts_res = await session.execute(select(Part))
            parts_map = {p.part_number.upper(): p.id for p in parts_res.scalars().all()}

            for r in rows:
                p_num = r.get("part_number", "").upper()
                part_id = parts_map.get(p_num)
                if not part_id:
                    continue  # Skip if part does not exist in master

                cost_rec = ComponentCost(
                    part_id=part_id,
                    period_start=r["period_start"],
                    raw_material_cost=r["raw_material_cost"],
                    process_cost=r["process_cost"],
                    overhead_cost=r["overhead_cost"],
                    tool_amortization=r["tool_amortization"],
                    total_cost=r["total_cost"],
                    source_system="INGESTION_FILE",
                )
                session.add(cost_rec)

        elif target == IngestionTarget.VEHICLE_BOM:
            # Prefetch model years and parts
            my_res = await session.execute(select(ModelYear))
            my_map = {my.year_code.upper(): my.id for my in my_res.scalars().all()}
            parts_res = await session.execute(select(Part))
            parts_map = {p.part_number.upper(): p.id for p in parts_res.scalars().all()}

            for r in rows:
                my_code = r.get("model_year_code", "").upper()
                p_num = r.get("part_number", "").upper()
                my_id = my_map.get(my_code)
                part_id = parts_map.get(p_num)

                if my_id and part_id:
                    bom_item = BomItem(
                        model_year_id=my_id,
                        part_id=part_id,
                        quantity_per_vehicle=r["quantity_per_vehicle"],
                    )
                    session.add(bom_item)
