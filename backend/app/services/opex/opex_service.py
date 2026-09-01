"""
Plant OPEX Service
Provides database queries, period aggregation, KPI calculations, and multi-plant benchmarking.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import logger
from calculations.opex.benchmark_methodology import BenchmarkMethodology
from calculations.opex.engine import OpexCalculationEngine
from calculations.opex.models import (
    BenchmarkMode,
    BenchmarkOpportunityResult,
    ComparabilityWeights,
    PlantKpiMetrics,
)
from database.models.plant_opex import BenchmarkRecord, OpexRecord, Plant


class PlantOpexService:
    """Orchestrates database retrieval and deterministic OPEX benchmark calculations."""

    @classmethod
    async def get_plant_kpis_for_period(
        cls,
        session: AsyncSession,
        plant_id: str,
        period_str: Optional[str] = None,
    ) -> Optional[PlantKpiMetrics]:
        """Calculates normalized operational KPIs for a plant in a specific period."""
        from backend.app.services.ingestion.unit_normalizer import UnitNormalizer

        # Query plant
        plant = await session.get(Plant, plant_id)
        if not plant:
            return None

        # Query latest or matching OpexRecord
        stmt = select(OpexRecord).where(OpexRecord.plant_id == plant_id)
        if period_str:
            parsed_d = UnitNormalizer.parse_date(period_str)
            if parsed_d:
                stmt = stmt.where(OpexRecord.period == parsed_d)
        stmt = stmt.order_by(OpexRecord.period.desc())

        res = await session.execute(stmt)
        record = res.scalars().first()
        if not record:
            return None

        # Helper decimal parser
        def _to_dec(val: Any) -> Optional[Decimal]:
            return Decimal(str(val)) if val is not None else None

        return OpexCalculationEngine.calculate_plant_kpis(
            plant_id=plant.id,
            plant_code=plant.plant_code,
            plant_name=plant.name,
            period_str=str(record.period),
            production_quantity=record.production_quantity,
            electricity_kwh=Decimal(str(record.electricity_kwh)),
            electricity_cost=Decimal(str(record.electricity_cost)),
            water_kl=Decimal(str(record.water_kl)),
            water_cost=Decimal(str(record.water_cost)),
            gas_consumption_nm3=Decimal(str(record.gas_consumption_nm3)),
            gas_cost=Decimal(str(record.gas_cost)),
            compressed_air_nm3=Decimal(str(record.compressed_air_nm3)),
            compressed_air_cost=Decimal(str(record.compressed_air_cost)),
            waste_quantity_mt=Decimal(str(record.waste_quantity_mt)),
            waste_cost=Decimal(str(record.waste_cost)),
            labor_cost=Decimal(str(record.labor_cost)),
            maintenance_cost=Decimal(str(record.maintenance_cost)),
            other_opex=Decimal(str(record.other_opex)),
            total_opex=Decimal(str(record.total_opex)),
            grid_kwh=_to_dec(record.grid_kwh),
            grid_cost_inr=_to_dec(record.grid_cost_inr),
            dg_kwh=_to_dec(record.dg_kwh),
            dg_cost_inr=_to_dec(record.dg_cost_inr),
            solar_kwh=_to_dec(record.solar_kwh),
            solar_cost_inr=_to_dec(record.solar_cost_inr),
            other_generated_kwh=_to_dec(record.other_generated_kwh),
            other_generation_cost_inr=_to_dec(record.other_generation_cost_inr),
            borewell_kl=_to_dec(record.borewell_kl),
            borewell_cost_inr=_to_dec(record.borewell_cost_inr),
            pwd_kl=_to_dec(record.pwd_kl),
            pwd_cost_inr=_to_dec(record.pwd_cost_inr),
            other_water_kl=_to_dec(record.other_water_kl),
            other_water_cost_inr=_to_dec(record.other_water_cost_inr),
            compressed_air_cf_total=_to_dec(record.compressed_air_cf_total),
            compressor_kwh_total=_to_dec(record.compressor_kwh_total),
            compressed_air_cost_inr=_to_dec(record.compressed_air_cost_allocated),
            is_compressor_power_embedded=record.is_compressor_power_embedded,
            gas_cf_total=_to_dec(record.gas_cf_total),
            gas_source_type=record.gas_source_type or "PNG",
            is_anomaly=record.is_anomaly,
        )

    @classmethod
    async def run_benchmark_analysis(
        cls,
        session: AsyncSession,
        target_plant_id: str,
        period_str: Optional[str] = None,
        mode: BenchmarkMode = BenchmarkMode.BEST_COMPARABLE,
        manual_target_opex_per_veh: Optional[Decimal] = None,
        manual_target_kwh_per_veh: Optional[Decimal] = None,
        manual_target_water_kl_per_veh: Optional[Decimal] = None,
        manual_target_air_cf_per_veh: Optional[Decimal] = None,
        manual_target_gas_cf_per_veh: Optional[Decimal] = None,
        weights: Optional[ComparabilityWeights] = None,
        fixed_overhead_ratio: Optional[Decimal] = None,
        persist_record: bool = False,
    ) -> Optional[BenchmarkOpportunityResult]:
        """
        Runs comprehensive multi-factor benchmark gap analysis against all peer plants.
        """
        target_kpi = await cls.get_plant_kpis_for_period(session, target_plant_id, period_str)
        if not target_kpi:
            return None

        target_plant = await session.get(Plant, target_plant_id)
        if not target_plant:
            return None

        all_plants_res = await session.execute(select(Plant))
        all_plants = all_plants_res.scalars().all()

        peer_kpis: List[PlantKpiMetrics] = []
        peer_metadata_map: Dict[str, Dict[str, Any]] = {}

        for p in all_plants:
            kpi = await cls.get_plant_kpis_for_period(session, p.id, period_str)
            if kpi:
                peer_kpis.append(kpi)
                peer_metadata_map[p.id] = {
                    "scope": p.manufacturing_scope or "FULL_VEHICLE_ASSEMBLY",
                    "capacity": p.annual_capacity_vehicles or 1000000,
                    "shifts": p.shifts_per_day or 3,
                    "tariff": p.grid_tariff_inr_kwh or Decimal("7.50"),
                }

        target_scope = target_plant.manufacturing_scope or "FULL_VEHICLE_ASSEMBLY"
        target_capacity = target_plant.annual_capacity_vehicles or 1000000
        target_shifts = target_plant.shifts_per_day or 3
        target_tariff = target_plant.grid_tariff_inr_kwh or Decimal("7.50")

        # Execute Benchmark Domain Logic
        result = BenchmarkMethodology.evaluate_benchmark_opportunity(
            target_plant_id=target_plant.id,
            target_plant_name=target_plant.name,
            target_kpi=target_kpi,
            target_scope=target_scope,
            target_capacity=target_capacity,
            target_shifts=target_shifts,
            target_tariff=target_tariff,
            peer_kpis=peer_kpis,
            peer_metadata_map=peer_metadata_map,
            mode=mode,
            manual_target_opex_per_veh=manual_target_opex_per_veh,
            manual_target_kwh_per_veh=manual_target_kwh_per_veh,
            manual_target_water_kl_per_veh=manual_target_water_kl_per_veh,
            manual_target_air_cf_per_veh=manual_target_air_cf_per_veh,
            manual_target_gas_cf_per_veh=manual_target_gas_cf_per_veh,
            weights=weights,
            fixed_overhead_ratio=fixed_overhead_ratio,
        )

        if persist_record:
            from backend.app.services.ingestion.unit_normalizer import UnitNormalizer

            parsed_period = UnitNormalizer.parse_date(target_kpi.period) or UnitNormalizer.parse_date("2024-04-01")
            bench_rec = BenchmarkRecord(
                benchmark_code=f"BMK-{target_plant.plant_code}-{mode.value[:4]}-{uuid.uuid4().hex[:6]}",
                benchmark_name=result.benchmark_source_name,
                benchmark_type=mode.value,
                plant_id=target_plant.id,
                period=parsed_period,
                kwh_per_vehicle=float(result.benchmark_kwh_per_vehicle),
                kl_per_vehicle=float(result.benchmark_water_kl_per_vehicle),
                gas_cf_per_vehicle=float(result.benchmark_gas_cf_per_vehicle) if result.benchmark_gas_cf_per_vehicle is not None else None,
                opex_per_vehicle=float(result.benchmark_total_opex_per_vehicle),
                compressed_air_cf_per_vehicle=float(result.benchmark_compressed_air_cf_per_vehicle) if result.benchmark_compressed_air_cf_per_vehicle is not None else None,
                compressor_kwh_per_cf=float(result.benchmark_compressor_kwh_per_cf) if result.benchmark_compressor_kwh_per_cf is not None else None,
                compressor_cf_per_kwh=float(result.benchmark_compressor_cf_per_kwh) if result.benchmark_compressor_cf_per_kwh is not None else None,
                comparability_index=float(result.benchmark_comparability_index),
                notes=f"Annual Opportunity: INR {result.gross_annual_opportunity_inr:.2f} ({result.gross_annual_opportunity_crores:.4f} Cr)",
            )
            session.add(bench_rec)
            await session.commit()

        return result
