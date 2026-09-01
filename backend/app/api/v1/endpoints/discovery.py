"""
Multi-Horizon Evidence Discovery API Endpoints
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.security import UserSession, get_current_user
from backend.app.services.applicability.applicability_engine import ApplicabilityMatrixEngine
from backend.app.services.discovery.discovery_service import DiscoveryService

router = APIRouter(prefix="/discovery", tags=["Multi-Horizon Evidence Discovery & Applicability Engine"])


class DiscoveredEvidenceItemResponse(BaseModel):
    evidence_type: str
    source_id: str
    code_or_number: str
    title: str
    status: str
    release_date: Optional[str] = None
    affected_part: Optional[str] = None
    affected_model: Optional[str] = None
    confidence: float
    match_reason: str


class EvidenceEvaluationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evidence_state: str
    confidence_score: float
    summary: str
    discovered_evidences: List[DiscoveredEvidenceItemResponse]
    applicable_models_count: int
    confirmed_models: List[str]
    unconfirmed_models: List[str]
    requires_human_review: bool
    review_reasons: List[str]
    provenance_details: Dict[str, Any]


class CrossModelSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    part_id: str
    part_number: str
    part_name: str
    component_code: str
    subsystem_code: str
    total_applicable_models: int
    applicable_models: List[Dict[str, Any]]
    active_model_years: List[int]
    sibling_models_sharing_part: List[str]
    implementation_records_count: int


@router.post("/evaluate-idea/{idea_id}", response_model=EvidenceEvaluationResponse)
async def evaluate_idea_evidence(
    idea_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """
    Runs multi-horizon evidence discovery over an idea and updates its evidence state.
    """
    service = DiscoveryService()
    try:
        result = await service.evaluate_idea_implementation_evidence(db, idea_id)
        # Convert date to string in items
        items = []
        for ev in result.discovered_evidences:
            items.append(
                DiscoveredEvidenceItemResponse(
                    evidence_type=ev.evidence_type,
                    source_id=ev.source_id,
                    code_or_number=ev.code_or_number,
                    title=ev.title,
                    status=ev.status,
                    release_date=str(ev.release_date) if ev.release_date else None,
                    affected_part=ev.affected_part,
                    affected_model=ev.affected_model,
                    confidence=ev.confidence,
                    match_reason=ev.match_reason,
                )
            )
        return EvidenceEvaluationResponse(
            evidence_state=result.evidence_state,
            confidence_score=result.confidence_score,
            summary=result.summary,
            discovered_evidences=items,
            applicable_models_count=result.applicable_models_count,
            confirmed_models=result.confirmed_models,
            unconfirmed_models=result.unconfirmed_models,
            requires_human_review=result.requires_human_review,
            review_reasons=result.review_reasons,
            provenance_details=result.provenance_details,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/cross-model-summary/{part_number}", response_model=CrossModelSummaryResponse)
async def get_cross_model_summary(
    part_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """
    Returns cross-model applicability matrix summary for a specific part number.
    """
    summary = await ApplicabilityMatrixEngine.get_cross_model_summary(db, part_number)
    if not summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Part {part_number} not found in master data.")
    return summary
