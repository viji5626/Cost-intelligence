"""
Unified Hybrid Retrieval API Endpoints
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import get_db
from backend.app.core.security import UserSession, get_current_user
from backend.app.services.retrieval.retrieval_service import RetrievalService
from ai.retrieval.benchmark import RetrievalBenchmarkHarness
from database.models.engineering_change import EngineeringChange
from database.models.ideathon import IdeaSubmission

router = APIRouter(prefix="/retrieval", tags=["Unified Hybrid Retrieval Engine"])


class SearchRequest(BaseModel):
    query: str = Field(..., description="Free text query or engineering identifier")
    target_vehicle_model: Optional[str] = Field(None, description="Optional vehicle model code filter")
    target_part_number: Optional[str] = Field(None, description="Optional part number filter")
    target_category: Optional[str] = Field(None, description="Optional cost reduction category filter")
    entity_type_filter: Optional[str] = Field(None, description="Filter by IDEA_SUBMISSION or ECN")
    top_k: int = Field(10, ge=1, le=50, description="Max candidates to return")
    enable_reranking: bool = Field(True, description="Enable local cross-encoder reranking")


class RetrievedDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_type: str
    entity_id: str
    text: str
    matched_strategy: str
    score: float
    initial_rank: int
    rerank_score: Optional[float]
    final_rank: Optional[int]
    part_number: Optional[str]
    model_code: Optional[str]
    category: Optional[str]
    metadata: Dict[str, Any]
    provenance_notes: str


@router.post("/search", response_model=List[RetrievedDocumentResponse])
async def search_hybrid(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """
    Executes hybrid multi-channel search combining Exact Identifier, Trigram Keyword,
    Dense Vector semantic search, RRF fusion, and Cross-Encoder reranking.
    """
    service = RetrievalService()
    results = await service.search(
        session=db,
        raw_query=request.query,
        target_vehicle_model=request.target_vehicle_model,
        target_part_number=request.target_part_number,
        target_category=request.target_category,
        entity_type_filter=request.entity_type_filter,
        top_k=request.top_k,
        enable_reranking=request.enable_reranking,
    )
    return results


@router.post("/index-all", status_code=status.HTTP_200_OK)
async def index_all_records(
    db: AsyncSession = Depends(get_db),
    current_user: UserSession = Depends(get_current_user),
):
    """
    Indexes all IdeaSubmissions and ECNs into the vector storage.
    """
    service = RetrievalService()
    ideas = (await db.execute(select(IdeaSubmission))).scalars().all()
    ecns = (await db.execute(select(EngineeringChange))).scalars().all()

    indexed_count = 0
    for idea in ideas:
        await service.index_idea_submission(db, idea)
        indexed_count += 1

    for ecn in ecns:
        await service.index_ecn(db, ecn)
        indexed_count += 1

    return {"status": "SUCCESS", "indexed_records": indexed_count}


@router.get("/benchmark", status_code=status.HTTP_200_OK)
async def run_retrieval_benchmark(
    current_user: UserSession = Depends(get_current_user),
):
    """
    Executes the 10 standard synthetic benchmark scenarios and returns quality metrics.
    """
    result = RetrievalBenchmarkHarness.run_benchmark()
    return result
