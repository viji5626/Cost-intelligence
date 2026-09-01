"""
Vehicle Ideathon API Endpoints
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.database import get_db
from backend.app.core.security import UserSession, get_current_user
from backend.app.services.ideathon.ideathon_service import IdeathonService
from database.models.ideathon import (
    CostReductionCategory,
    DataQualityStatus,
    IdeaDecisionState,
    IdeaSubmission,
    ImplementationEvidenceState,
)

router = APIRouter(prefix="/ideathon", tags=["Vehicle Ideathon Domain Engine"])


class IdeaSubmitRequest(BaseModel):
    title: str = Field(..., description="Raw title of the cost reduction idea")
    description: str = Field(..., description="Detailed problem and proposed solution")
    submitter_employee_id: Optional[str] = Field(None, description="Employee ID of submitter")
    submitter_plant_code: Optional[str] = Field(None, description="Plant origin code")
    claimed_saving_per_veh: Optional[Decimal] = Field(None, description="Submitter estimated savings in INR")


class IdeaSubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    submission_code: str
    raw_title: str
    raw_description: str
    decomposed_problem: Optional[str]
    decomposed_solution: Optional[str]
    decomposed_expected_benefit: Optional[str]
    extracted_part_number: Optional[str]
    extracted_part_name: Optional[str]
    is_bom_linked: bool
    cost_reduction_category: str
    decision_state: str
    evidence_state: str
    data_quality: str
    extraction_confidence: float
    raw_claimed_saving_per_veh: Optional[Decimal]
    created_at: Any


@router.post("/submit", response_model=IdeaSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def submit_idea(
    req: IdeaSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> IdeaSubmission:
    """
    Submits a vehicle cost reduction idea, extracts engineering entities,
    maps to vehicle hierarchy, and detects near-duplicates.
    """
    idea = await IdeathonService.submit_and_normalize_idea(
        session=db,
        title=req.title,
        description=req.description,
        submitter_employee_id=req.submitter_employee_id or current_user.user_id,
        submitter_plant_code=req.submitter_plant_code,
        raw_claimed_saving=float(req.claimed_saving_per_veh) if req.claimed_saving_per_veh else None,
    )
    return idea


@router.get("/ideas", response_model=List[IdeaSubmissionResponse], status_code=status.HTTP_200_OK)
async def list_ideas(
    decision_state: Optional[IdeaDecisionState] = Query(None),
    data_quality: Optional[DataQualityStatus] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> List[IdeaSubmission]:
    """Lists ideas with optional filtering by decision state or data quality."""
    return await IdeathonService.get_ideas(
        session=db,
        decision_state=decision_state.value if decision_state else None,
        data_quality=data_quality.value if data_quality else None,
        limit=limit,
    )


@router.get("/review-queue", response_model=List[IdeaSubmissionResponse], status_code=status.HTTP_200_OK)
async def get_human_review_queue(
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> List[IdeaSubmission]:
    """Retrieves submissions flagged as ambiguous or requiring human review."""
    return await IdeathonService.get_human_review_queue(db)


@router.get("/ideas/{idea_id}", response_model=IdeaSubmissionResponse, status_code=status.HTTP_200_OK)
async def get_idea_detail(
    idea_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
) -> IdeaSubmission:
    """Retrieves single idea details by ID."""
    idea = await db.get(IdeaSubmission, idea_id)
    if not idea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Idea '{idea_id}' not found")
    return idea
