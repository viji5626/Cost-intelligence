"""
Vehicle Ideathon Service
Orchestrates raw idea ingestion, taxonomy mapping, database relational linking,
duplicate detection foundation, clustering, and human review routing.
"""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ai.ideathon.normalizer import IdeaNormalizer, NormalizedIdeaResult
from backend.app.core.logging import logger
from database.models.ideathon import (
    DataQualityStatus,
    IdeaCluster,
    IdeaDecisionState,
    IdeaDuplicateLink,
    IdeaSubmission,
    ImplementationEvidenceState,
)
from database.models.part_bom import Component, Part, Subsystem
from database.models.vehicle_hierarchy import Vehicle, VehicleModel


class IdeathonService:
    """Enterprise service for Vehicle Cost Reduction Ideathon engine."""

    @classmethod
    async def submit_and_normalize_idea(
        cls,
        session: AsyncSession,
        title: str,
        description: str,
        submitter_employee_id: Optional[str] = None,
        submitter_plant_code: Optional[str] = None,
        raw_claimed_saving: Optional[float] = None,
    ) -> IdeaSubmission:
        """
        Ingests a raw idea, extracts entities, resolves foreign keys against master data,
        identifies near-duplicates, and persists the record.
        """
        # 1. Normalize and extract entities
        norm = IdeaNormalizer.normalize_submission(title, description, raw_claimed_saving)
        submission_code = f"IDEA-{uuid.uuid4().hex[:8].upper()}"

        # 2. Query Authoritative Relational Master Data
        target_veh_id: Optional[str] = None
        target_model_id: Optional[str] = None
        target_part_id: Optional[str] = None
        target_subsystem_id: Optional[str] = None
        target_comp_id: Optional[str] = None

        if norm.extracted_vehicle_alias:
            # Query vehicle models by name
            alias_clean = norm.extracted_vehicle_alias.replace("_", " ").title()
            model_res = await session.execute(
                select(VehicleModel).where(VehicleModel.name.ilike(f"%{alias_clean}%"))
            )
            v_model = model_res.scalars().first()
            if v_model:
                target_model_id = v_model.id
                target_veh_id = v_model.vehicle_id

        if norm.extracted_part_number:
            # Query part by exact part_number
            part_res = await session.execute(
                select(Part).where(Part.part_number == norm.extracted_part_number)
            )
            part = part_res.scalars().first()
            if part:
                target_part_id = part.id
                target_comp_id = part.component_id

        # 3. Create IdeaSubmission Instance
        idea = IdeaSubmission(
            submission_code=submission_code,
            raw_title=norm.raw_title,
            raw_description=norm.raw_description,
            submitter_employee_id=submitter_employee_id,
            submitter_plant_code=submitter_plant_code,
            raw_claimed_saving_per_veh=norm.claimed_saving_per_veh,
            decomposed_problem=norm.decomposed_problem,
            decomposed_solution=norm.decomposed_solution,
            decomposed_expected_benefit=norm.decomposed_expected_benefit,
            target_vehicle_id=target_veh_id,
            target_model_id=target_model_id,
            target_part_id=target_part_id,
            target_component_id=target_comp_id,
            extracted_part_number=norm.extracted_part_number,
            extracted_part_name=norm.extracted_component_alias,
            extracted_synonyms=norm.extracted_synonyms,
            is_bom_linked=norm.is_bom_linked,
            cost_reduction_category=norm.cost_reduction_category.value,
            decision_state=IdeaDecisionState.SUBMITTED.value,
            evidence_state=ImplementationEvidenceState.NOT_EVALUATED.value,
            data_quality=norm.data_quality.value,
            extraction_confidence=norm.extraction_confidence,
            part_match_confidence=norm.part_match_confidence,
        )
        session.add(idea)
        await session.flush()

        # 4. Duplicate & Synergy Detection against existing submissions
        existing_res = await session.execute(
            select(IdeaSubmission).where(IdeaSubmission.id != idea.id).limit(100)
        )
        existing_ideas = existing_res.scalars().all()

        for ex in existing_ideas:
            sim = IdeaNormalizer.calculate_idea_similarity(
                idea.raw_title, idea.raw_description, ex.raw_title, ex.raw_description
            )
            if sim >= 0.75:
                dup_type = "EXACT_DUPLICATE" if sim >= 0.95 else "NEAR_DUPLICATE_SAME_VEHICLE"
                dup_link = IdeaDuplicateLink(
                    source_idea_id=idea.id,
                    target_idea_id=ex.id,
                    similarity_score=sim,
                    duplicate_type=dup_type,
                    explanation=f"High lexical similarity ({sim * 100:.1f}%) with {ex.submission_code}",
                )
                session.add(dup_link)

        await session.commit()
        await session.refresh(idea)
        logger.info(f"Normalized idea [{idea.submission_code}]: category={idea.cost_reduction_category}, quality={idea.data_quality}")
        return idea

    @classmethod
    async def get_ideas(
        cls,
        session: AsyncSession,
        decision_state: Optional[str] = None,
        data_quality: Optional[str] = None,
        limit: int = 50,
    ) -> List[IdeaSubmission]:
        """Retrieves idea submissions with optional filtering."""
        stmt = select(IdeaSubmission).order_by(IdeaSubmission.created_at.desc()).limit(limit)
        if decision_state:
            stmt = stmt.where(IdeaSubmission.decision_state == decision_state)
        if data_quality:
            stmt = stmt.where(IdeaSubmission.data_quality == data_quality)

        res = await session.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_human_review_queue(cls, session: AsyncSession) -> List[IdeaSubmission]:
        """Retrieves submissions flagged as requiring human review or having ambiguous extractions."""
        stmt = select(IdeaSubmission).where(
            or_(
                IdeaSubmission.data_quality == DataQualityStatus.REQUIRES_HUMAN_REVIEW.value,
                IdeaSubmission.data_quality == DataQualityStatus.AMBIGUOUS_VEHICLE.value,
                IdeaSubmission.data_quality == DataQualityStatus.AMBIGUOUS_COMPONENT.value,
                IdeaSubmission.data_quality == DataQualityStatus.MISSING_DATA.value,
            )
        ).order_by(IdeaSubmission.created_at.desc())

        res = await session.execute(stmt)
        return list(res.scalars().all())
