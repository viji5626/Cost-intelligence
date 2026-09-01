"""
Plant OPEX & Benchmark Methodology API Endpoints
"""

from decimal import Decimal
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.security import UserSession, get_current_user
from backend.app.services.opex.opex_service import PlantOpexService
from calculations.opex.models import (
    BenchmarkMode,
    BenchmarkOpportunityResult,
    ComparabilityWeights,
    PlantKpiMetrics,
)
from database.models.plant_opex import Plant

router = APIRouter(prefix="/opex", tags=["Plant OPEX & Benchmarking"])


class BenchmarkCompareRequest(BaseModel):
    target_plant_id: str
    period: Optional[str] = None
    mode: BenchmarkMode = BenchmarkMode.BEST_COMPARABLE
    manual_target_opex_per_veh: Optional[Decimal] = None
    manual_target_kwh_per_veh: Optional[Decimal] = None
    weights: Optional[ComparabilityWeights] = None
    fixed_overhead_ratio: Optional[Decimal] = None  # Initial default 0.30 - to be calibrated with customer data
    persist_record: bool = False


@router.get("/kpis/{plant_id}", response_model=PlantKpiMetrics, status_code=status.HTTP_200_OK)
async def get_plant_kpis(
    plant_id: str,
    period: Optional[str] = Query(None, description="Format YYYY-MM-DD or YYYY-MM"),
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> PlantKpiMetrics:
    """Retrieves calculated operational and financial KPIs per vehicle for a plant."""
    kpis = await PlantOpexService.get_plant_kpis_for_period(db, plant_id, period)
    if not kpis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No OPEX records found for plant_id '{plant_id}'",
        )
    return kpis


@router.post("/benchmark/compare", response_model=BenchmarkOpportunityResult, status_code=status.HTTP_200_OK)
async def compare_plant_benchmark(
    req: BenchmarkCompareRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> BenchmarkOpportunityResult:
    """
    Performs deterministic multi-factor benchmark gap analysis, comparability scoring,
    variance decomposition, and gross annual financial opportunity quantification.
    """
    res = await PlantOpexService.run_benchmark_analysis(
        session=db,
        target_plant_id=req.target_plant_id,
        period_str=req.period,
        mode=req.mode,
        manual_target_opex_per_veh=req.manual_target_opex_per_veh,
        manual_target_kwh_per_veh=req.manual_target_kwh_per_veh,
        weights=req.weights,
        fixed_overhead_ratio=req.fixed_overhead_ratio,
        persist_record=req.persist_record,
    )
    if not res:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unable to run benchmark analysis for plant_id '{req.target_plant_id}'",
        )
    return res


@router.get("/summary", response_model=List[PlantKpiMetrics], status_code=status.HTTP_200_OK)
async def get_all_plants_latest_kpis(
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> List[PlantKpiMetrics]:
    """Retrieves latest KPI metrics across all manufacturing plants in the portfolio."""
    all_plants_res = await db.execute(select(Plant))
    all_plants = all_plants_res.scalars().all()

    kpi_list: List[PlantKpiMetrics] = []
    for p in all_plants:
        kpi = await PlantOpexService.get_plant_kpis_for_period(db, p.id)
        if kpi:
            kpi_list.append(kpi)

    return kpi_list
