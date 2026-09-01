"""
Evidence Discovery Orchestrator Service
Orchestrates multi-horizon evidence discovery for Idea Submissions using hybrid retrieval,
cross-model applicability matrix, and deterministic state evaluation.
"""

from datetime import date
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.applicability.applicability_engine import ApplicabilityMatrixEngine
from backend.app.services.discovery.evidence_discovery_engine import (
    DiscoveredEvidenceItem,
    EvidenceDiscoveryEngine,
    EvidenceEvaluationResult,
)
from backend.app.services.retrieval.retrieval_service import RetrievalService
from database.models.engineering_change import EngineeringChange, Implementation
from database.models.ideathon import IdeaSubmission


class DiscoveryService:
    """
    Master service for running evidence discovery across ideas and portfolio records.
    """

    def __init__(self):
        self.retrieval_service = RetrievalService()

    async def evaluate_idea_implementation_evidence(
        self,
        session: AsyncSession,
        idea_id: str,
    ) -> EvidenceEvaluationResult:
        """
        Executes multi-horizon evidence discovery for a single IdeaSubmission:
        1. Queries cross-model applicability for target part/component.
        2. Retrieves candidate ECNs and Implementation records via Hybrid Retrieval.
        3. Evaluates 7-state implementation taxonomy deterministically.
        4. Updates idea.evidence_state in database.
        """
        stmt = select(IdeaSubmission).where(IdeaSubmission.id == idea_id)
        res = await session.execute(stmt)
        idea = res.scalars().first()
        if not idea:
            raise ValueError(f"IdeaSubmission with ID {idea_id} not found.")

        # 1. Get cross-model applicability summary
        applicable_sibling_models: List[str] = []
        if idea.extracted_part_number:
            summary = await ApplicabilityMatrixEngine.get_cross_model_summary(
                session, idea.extracted_part_number
            )
            if summary:
                applicable_sibling_models = summary.sibling_models_sharing_part

        # 2. Search candidate ECNs using hybrid retrieval
        search_query = f"{idea.extracted_part_number or ''} {idea.raw_title}"
        retrieved_docs = await self.retrieval_service.search(
            session=session,
            raw_query=search_query,
            target_vehicle_model=idea.target_model_id,
            target_part_number=idea.extracted_part_number,
            entity_type_filter="ECN",
            top_k=10,
            enable_reranking=True,
        )

        discovered_items: List[DiscoveredEvidenceItem] = []
        for doc in retrieved_docs:
            # Query actual ECN details
            ecn_res = await session.execute(select(EngineeringChange).where(EngineeringChange.id == doc.entity_id))
            ecn = ecn_res.scalars().first()
            if ecn:
                discovered_items.append(
                    DiscoveredEvidenceItem(
                        evidence_type="ECN",
                        source_id=ecn.id,
                        code_or_number=ecn.ecn_number,
                        title=ecn.title,
                        status=ecn.status,
                        release_date=ecn.release_date,
                        affected_part=doc.part_number or idea.extracted_part_number,
                        affected_model=doc.model_code,
                        confidence=doc.rerank_score or doc.score,
                        match_reason=doc.provenance_notes,
                        is_conflicting=ecn.status in ["CONFLICTING", "CANCELLED"],
                        is_obsolete=ecn.status == "OBSOLETE",
                    )
                )

        # Also search direct database implementations for exact part
        if idea.target_part_id:
            impl_res = await session.execute(
                select(Implementation).where(Implementation.part_id == idea.target_part_id)
            )
            for impl in impl_res.scalars().all():
                discovered_items.append(
                    DiscoveredEvidenceItem(
                        evidence_type="IMPLEMENTATION_RECORD",
                        source_id=impl.id,
                        code_or_number=f"IMPL-{impl.id[:8]}",
                        title=f"Verified Implementation ({impl.verification_source})",
                        status=impl.status,
                        release_date=impl.implementation_date,
                        affected_part=idea.extracted_part_number,
                        affected_model=idea.target_model_id,
                        confidence=impl.confidence_score,
                        match_reason="Direct database implementation link",
                    )
                )

        # 3. Deterministic State Evaluation
        submission_date = idea.created_at.date() if hasattr(idea.created_at, "date") else date.today()
        eval_result = EvidenceDiscoveryEngine.evaluate_implementation_evidence(
            target_part_number=idea.extracted_part_number,
            target_model_code=idea.target_model_id,
            submission_date=submission_date,
            retrieved_evidences=discovered_items,
            applicable_sibling_models=applicable_sibling_models,
        )

        # 4. Update IdeaSubmission in database
        idea.evidence_state = eval_result.evidence_state
        await session.commit()

        return eval_result
