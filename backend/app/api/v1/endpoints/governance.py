"""
Governance & Human-in-the-Loop Review Endpoints
Provides review queue management, confidence calibration inspector, reviewer actions, and high-value business case consolidator.
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.core.database import get_db
from backend.app.core.security import UserSession, get_current_user
from backend.app.services.governance.confidence_engine import CalibratedConfidenceResult, ConfidenceCalibrationEngine
from backend.app.services.governance.governance_service import GovernanceService
from database.models.governance import IdeaReviewRecord
from database.models.ideathon import IdeaSubmission

router = APIRouter(prefix="/governance", tags=["Human-in-the-Loop Governance"])


class ReviewActionRequest(BaseModel):
    action_type: str = Field(description="APPROVE, REJECT, OVERRIDE, REQUEST_MORE_EVIDENCE, ESCALATE, REOPEN")
    comments: Optional[str] = Field(default=None, description="Reviewer feedback or notes")
    override_rationale: Optional[str] = Field(default=None, description="Mandatory rationale when overriding system recommendation")
    target_decision_state: Optional[str] = Field(default=None, description="Target IdeaDecisionState when overriding")


class ReviewAssignRequest(BaseModel):
    reviewer_user_id: str = Field(description="Target reviewer User ID")


class ConfidenceEvaluateRequest(BaseModel):
    source_authority: str = "ERP_SAP"
    exact_identifier_matched: bool = True
    is_synonym_match: bool = False
    retrieval_relevance: float = 1.0
    corroborating_sources_count: int = 1
    has_ecn_record: bool = True
    has_bom_record: bool = True
    has_effective_dates: bool = True
    entity_extraction_confidence: float = 1.0
    has_conflicting_records: bool = False


@router.post("/sync/{idea_id}")
async def sync_idea_review_endpoint(
    idea_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """
    Evaluates calibrated confidence and review priority routing for an idea submission.
    """
    service = GovernanceService()
    try:
        record = await service.sync_idea_review_record(db, idea_id)
        return record
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/queue")
async def list_review_queue_endpoint(
    review_status: Optional[str] = Query(default=None),
    priority: Optional[str] = Query(default=None),
    is_safety_critical: Optional[bool] = Query(default=None),
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """
    Lists ideas in the human review queue sorted by priority tier (CRITICAL_P0 -> HIGH_P1 -> MEDIUM_P2 -> LOW_P3).
    """
    service = GovernanceService()
    items = await service.list_review_queue(
        db=db,
        status=review_status,
        priority=priority,
        is_safety_critical=is_safety_critical,
        limit=limit,
        offset=offset,
    )
    return items


@router.post("/assign/{idea_id}")
async def assign_reviewer_endpoint(
    idea_id: str,
    request: ReviewAssignRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """
    Assigns a specialist reviewer to an idea item.
    """
    service = GovernanceService()
    try:
        record = await service.assign_reviewer(
            db=db,
            idea_id=idea_id,
            reviewer_user_id=request.reviewer_user_id,
            actor_user=current_user,
        )
        return record
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/action/{idea_id}")
async def perform_review_action_endpoint(
    idea_id: str,
    request: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """
    Executes a formal review action (APPROVE, REJECT, OVERRIDE, REQUEST_MORE_EVIDENCE, ESCALATE, REOPEN).
    """
    service = GovernanceService()
    try:
        record = await service.perform_review_action(
            db=db,
            idea_id=idea_id,
            actor_user=current_user,
            action_type=request.action_type,
            comments=request.comments,
            override_rationale=request.override_rationale,
            target_decision_state=request.target_decision_state,
        )
        return record
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/calculate-confidence", response_model=CalibratedConfidenceResult)
async def calculate_confidence_endpoint(
    request: ConfidenceEvaluateRequest,
    current_user: UserSession = Depends(get_current_user),
):
    """
    Inspects calibrated confidence calculation for given evidence attributes.
    """
    return ConfidenceCalibrationEngine.calculate_confidence(
        source_authority=request.source_authority,
        exact_identifier_matched=request.exact_identifier_matched,
        is_synonym_match=request.is_synonym_match,
        retrieval_relevance=request.retrieval_relevance,
        corroborating_sources_count=request.corroborating_sources_count,
        has_ecn_record=request.has_ecn_record,
        has_bom_record=request.has_bom_record,
        has_effective_dates=request.has_effective_dates,
        entity_extraction_confidence=request.entity_extraction_confidence,
        has_conflicting_records=request.has_conflicting_records,
    )


@router.get("/review-case/{idea_id}")
async def get_high_value_business_case_endpoint(
    idea_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """
    Consolidates the complete High-Value Business Case view for an idea:
    Idea -> Applicable Models -> Implementation Evidence -> Costs & Volumes -> Opportunity -> Confidence -> Review Audit.
    """
    stmt = (
        select(IdeaSubmission)
        .where(IdeaSubmission.id == idea_id)
        .options(
            selectinload(IdeaSubmission.opportunity_evaluation),
            selectinload(IdeaSubmission.review_record).selectinload(IdeaReviewRecord.actions),
        )
    )
    idea = (await db.execute(stmt)).scalars().first()
    if not idea:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Idea not found: {idea_id}")

    opp = idea.opportunity_evaluation
    rev = idea.review_record

    return {
        "idea_id": idea.id,
        "submission_code": idea.submission_code,
        "raw_title": idea.raw_title,
        "raw_description": idea.raw_description,
        "extracted_part_number": idea.extracted_part_number,
        "cost_reduction_category": idea.cost_reduction_category,
        "dimensions": {
            "ai_calibrated_confidence": rev.calibrated_confidence_score if rev else None,
            "confidence_tier": rev.confidence_tier if rev else None,
            "implementation_evidence_state": idea.evidence_state,
            "idea_business_decision_state": idea.decision_state,
            "human_review_status": rev.review_status if rev else "NOT_EVALUATED",
            "review_priority": rev.review_priority if rev else None,
            "is_safety_critical": rev.is_safety_critical if rev else False,
            "routing_reasons": rev.routing_reasons if rev else [],
        },
        "financial_opportunity": {
            "current_piece_cost_inr": float(opp.current_piece_cost_inr) if opp and opp.current_piece_cost_inr else None,
            "proposed_piece_cost_inr": float(opp.proposed_piece_cost_inr) if opp and opp.proposed_piece_cost_inr else None,
            "saving_per_vehicle_inr": float(opp.saving_per_vehicle_inr) if opp and opp.saving_per_vehicle_inr else None,
            "applicable_annual_volume": opp.applicable_annual_volume if opp else 0,
            "gross_annual_opportunity_inr": float(opp.gross_annual_opportunity_inr) if opp and opp.gross_annual_opportunity_inr else None,
            "tooling_investment_inr": float(opp.tooling_investment_inr) if opp and opp.tooling_investment_inr else 0.0,
            "validation_investment_inr": float(opp.validation_investment_inr) if opp and opp.validation_investment_inr else 0.0,
            "net_opportunity_inr": float(opp.net_opportunity_inr) if opp and opp.net_opportunity_inr else None,
            "payback_period_years": opp.payback_period_years if opp else None,
            "applicable_models": opp.applicable_models if opp else [],
            "provenance_hash": opp.provenance_hash if opp else None,
        },
        "review_actions_history": [
            {
                "id": a.id,
                "actor_user_id": a.actor_user_id,
                "action_type": a.action_type,
                "previous_status": a.previous_status,
                "new_status": a.new_status,
                "reviewer_comments": a.reviewer_comments,
                "override_rationale": a.override_rationale,
                "created_at": a.created_at,
            }
            for a in (rev.actions if rev else [])
        ],
    }
