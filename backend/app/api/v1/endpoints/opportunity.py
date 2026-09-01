"""
Opportunity Evaluation & Financial Simulation Endpoints
Provides deterministic vehicle cost reduction calculations and what-if simulation APIs.
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.security import UserSession, get_current_user
from backend.app.services.opportunity.opportunity_engine import OpportunityCalculationResult, VehicleOpportunityEngine
from backend.app.services.opportunity.opportunity_service import OpportunityService
from database.models.ideathon import IdeaOpportunityEvaluation

router = APIRouter(prefix="/opportunity", tags=["Vehicle Cost Opportunity"])


class OpportunityEvaluateRequest(BaseModel):
    tooling_investment: float = Field(default=0.0, description="Tooling/die investment in INR")
    validation_investment: float = Field(default=0.0, description="Testing and validation investment in INR")
    effective_calendar_year: Optional[int] = Field(default=None, description="Starting calendar year for model volume")
    override_proposed_cost: Optional[float] = Field(default=None, description="Explicit proposed piece cost in INR")


class OpportunitySimulateRequest(BaseModel):
    current_piece_cost: Optional[float] = Field(default=None, description="Current baseline part cost in INR")
    proposed_piece_cost: Optional[float] = Field(default=None, description="Proposed part cost in INR")
    raw_claimed_saving: Optional[float] = Field(default=None, description="Claimed saving per vehicle in INR")
    volumes_by_model: Dict[str, int] = Field(default_factory=dict, description="Planned annual volume per model")
    applicable_models: List[str] = Field(default_factory=list, description="Applicable model codes")
    tooling_investment: float = Field(default=0.0, description="Tooling investment in INR")
    validation_investment: float = Field(default=0.0, description="Validation investment in INR")
    effective_calendar_year: Optional[int] = Field(default=None, description="Effective calendar year filter")
    model_year_calendar_years: Optional[Dict[str, int]] = Field(default=None, description="Mapping of model to calendar year")


@router.post("/evaluate-idea/{idea_id}", response_model=OpportunityCalculationResult)
async def evaluate_idea_opportunity_endpoint(
    idea_id: str,
    request: OpportunityEvaluateRequest = OpportunityEvaluateRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """
    Evaluates and persists deterministic opportunity valuation for an idea submission.
    """
    service = OpportunityService()
    try:
        result = await service.evaluate_idea_opportunity(
            db=db,
            idea_id=idea_id,
            tooling_investment=request.tooling_investment,
            validation_investment=request.validation_investment,
            effective_calendar_year=request.effective_calendar_year,
            override_proposed_cost=request.override_proposed_cost,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Opportunity calculation failed: {str(e)}")


@router.post("/simulate", response_model=OpportunityCalculationResult)
async def simulate_opportunity_endpoint(
    request: OpportunitySimulateRequest,
    current_user: UserSession = Depends(get_current_user),
):
    """
    Simulates what-if vehicle cost reduction opportunity without modifying database state.
    """
    result = VehicleOpportunityEngine.calculate_opportunity(
        current_piece_cost=request.current_piece_cost,
        proposed_piece_cost=request.proposed_piece_cost,
        volumes_by_model=request.volumes_by_model,
        applicable_model_codes=request.applicable_models,
        tooling_investment=request.tooling_investment,
        validation_investment=request.validation_investment,
        effective_calendar_year=request.effective_calendar_year,
        model_year_calendar_years=request.model_year_calendar_years,
        raw_claimed_saving=request.raw_claimed_saving,
    )
    return result


@router.get("/idea/{idea_id}", response_model=OpportunityCalculationResult)
async def get_idea_opportunity_endpoint(
    idea_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """
    Retrieves the latest persisted deterministic opportunity valuation for an idea.
    """
    stmt = select(IdeaOpportunityEvaluation).where(IdeaOpportunityEvaluation.idea_id == idea_id)
    record = (await db.execute(stmt)).scalars().first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Opportunity valuation not found for idea: {idea_id}")

    return OpportunityCalculationResult(
        status=record.status,
        current_piece_cost_inr=float(record.current_piece_cost_inr) if record.current_piece_cost_inr else None,
        proposed_piece_cost_inr=float(record.proposed_piece_cost_inr) if record.proposed_piece_cost_inr else None,
        saving_per_vehicle_inr=float(record.saving_per_vehicle_inr) if record.saving_per_vehicle_inr else None,
        applicable_annual_volume=record.applicable_annual_volume,
        gross_annual_opportunity_inr=float(record.gross_annual_opportunity_inr) if record.gross_annual_opportunity_inr else None,
        tooling_investment_inr=float(record.tooling_investment_inr) if record.tooling_investment_inr else 0.0,
        validation_investment_inr=float(record.validation_investment_inr) if record.validation_investment_inr else 0.0,
        net_opportunity_inr=float(record.net_opportunity_inr) if record.net_opportunity_inr else None,
        payback_period_years=record.payback_period_years,
        payback_period_months=record.payback_period_months,
        applicable_models=record.applicable_models or [],
        volume_by_model=record.volume_by_model or {},
        effective_model_year=record.effective_model_year,
        formula_version=record.formula_version,
        provenance_hash=record.provenance_hash,
        provenance_metadata=record.provenance_metadata or {},
    )
