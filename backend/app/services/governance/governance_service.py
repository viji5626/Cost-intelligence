"""
Governance & Human-in-the-Loop Review Workflow Service
Orchestrates the review queue state machine, confidence calibration, reviewer assignments, and immutable override logs.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.core.security import UserSession
from backend.app.services.governance.confidence_engine import ConfidenceCalibrationEngine, ReviewPrioritizer
from database.models.audit import AuditLog
from database.models.governance import (
    IdeaReviewAction,
    IdeaReviewRecord,
    ReviewActionType,
    ReviewPriority,
    ReviewStatus,
)
from database.models.ideathon import (
    IdeaDecisionState,
    IdeaOpportunityEvaluation,
    IdeaSubmission,
    ImplementationEvidenceState,
)
from database.models.part_bom import Part, Subsystem


class GovernanceService:
    """
    Service layer governing human-in-the-loop workflows, calibrated confidence evaluation, and immutable audit logs.
    """

    ALLOWED_REVIEWER_ROLES = {"ADMIN", "COST_ENGINEER", "VAVE_COMMITTEE", "CHIEF_ENGINEER"}

    async def sync_idea_review_record(self, db: AsyncSession, idea_id: str) -> IdeaReviewRecord:
        """
        Evaluates evidence confidence and priority routing to create or update an IdeaReviewRecord.
        """
        stmt = (
            select(IdeaSubmission)
            .where(IdeaSubmission.id == idea_id)
            .options(
                selectinload(IdeaSubmission.review_record),
                selectinload(IdeaSubmission.opportunity_evaluation),
            )
        )
        idea = (await db.execute(stmt)).scalars().first()
        if not idea:
            raise ValueError(f"IdeaSubmission not found: {idea_id}")

        # 1. Fetch Part & Subsystem
        subsystem_code: Optional[str] = None
        is_safety = False
        if idea.target_part_id:
            part = (await db.execute(select(Part).where(Part.id == idea.target_part_id))).scalars().first()
            if part:
                is_safety = part.is_safety_critical
                if part.component_id:
                    # Check Subsystem
                    sub_stmt = (
                        select(Subsystem.code)
                        .select_from(Part)
                        .where(Part.id == part.id)
                    )
        elif idea.target_subsystem_id:
            sub = (await db.execute(select(Subsystem).where(Subsystem.id == idea.target_subsystem_id))).scalars().first()
            if sub:
                subsystem_code = sub.code

        # 2. Compute Calibrated Confidence
        has_conflict = idea.evidence_state == ImplementationEvidenceState.CONFLICTING_EVIDENCE.value
        has_ecn = idea.evidence_state in (
            ImplementationEvidenceState.IMPLEMENTATION_CONFIRMED.value,
            ImplementationEvidenceState.PARTIALLY_CONFIRMED.value,
            ImplementationEvidenceState.HISTORICAL_IMPLEMENTATION.value,
        )
        confidence_result = ConfidenceCalibrationEngine.calculate_confidence(
            source_authority="ERP_SAP" if idea.is_bom_linked else "UNOFFICIAL",
            exact_identifier_matched=bool(idea.extracted_part_number),
            retrieval_relevance=float(idea.part_match_confidence),
            has_ecn_record=has_ecn,
            has_bom_record=idea.is_bom_linked,
            entity_extraction_confidence=float(idea.extraction_confidence),
            has_conflicting_records=has_conflict,
        )

        # 3. Compute Net Financial Opportunity
        net_opp: Optional[float] = None
        if idea.opportunity_evaluation and idea.opportunity_evaluation.net_opportunity_inr:
            net_opp = float(idea.opportunity_evaluation.net_opportunity_inr)

        # 4. Compute Deterministic Review Priority & Routing
        routing_result = ReviewPrioritizer.evaluate_routing(
            subsystem_code=subsystem_code,
            is_part_safety_critical=is_safety,
            evidence_state=idea.evidence_state,
            data_quality=idea.data_quality,
            calibrated_confidence_score=confidence_result.composite_score,
            net_opportunity_inr=net_opp,
        )

        # 5. Update or Create Review Record
        record = idea.review_record
        if not record:
            initial_status = ReviewStatus.PENDING_REVIEW.value if routing_result.requires_human_review else ReviewStatus.NOT_REQUIRED.value
            record = IdeaReviewRecord(
                idea_id=idea.id,
                review_status=initial_status,
                review_priority=routing_result.review_priority,
                routing_reasons=routing_result.routing_reasons,
                is_safety_critical=routing_result.is_safety_critical,
                calibrated_confidence_score=confidence_result.composite_score,
                confidence_tier=confidence_result.confidence_tier,
                confidence_breakdown=confidence_result.breakdown_metadata,
                original_automated_decision="RECOMMENDED_FOR_STUDY" if confidence_result.composite_score >= 0.70 else "REQUIRES_REVIEW",
                original_evidence_state=idea.evidence_state,
            )
            db.add(record)
        else:
            record.review_priority = routing_result.review_priority
            record.routing_reasons = routing_result.routing_reasons
            record.is_safety_critical = routing_result.is_safety_critical
            record.calibrated_confidence_score = confidence_result.composite_score
            record.confidence_tier = confidence_result.confidence_tier
            record.confidence_breakdown = confidence_result.breakdown_metadata

        await db.commit()
        await db.refresh(record)
        return record

    async def list_review_queue(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        is_safety_critical: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[IdeaReviewRecord]:
        """
        Fetches review records ordered by priority (P0 -> P1 -> P2 -> P3) and creation timestamp.
        """
        stmt = (
            select(IdeaReviewRecord)
            .options(selectinload(IdeaReviewRecord.actions))
            .order_by(IdeaReviewRecord.review_priority.asc(), IdeaReviewRecord.created_at.desc())
        )
        if status:
            stmt = stmt.where(IdeaReviewRecord.review_status == status)
        if priority:
            stmt = stmt.where(IdeaReviewRecord.review_priority == priority)
        if is_safety_critical is not None:
            stmt = stmt.where(IdeaReviewRecord.is_safety_critical == is_safety_critical)

        stmt = stmt.offset(offset).limit(limit)
        return list((await db.execute(stmt)).scalars().all())

    async def assign_reviewer(
        self,
        db: AsyncSession,
        idea_id: str,
        reviewer_user_id: str,
        actor_user: UserSession,
    ) -> IdeaReviewRecord:
        """Assigns an expert reviewer to an idea review item."""
        self._check_reviewer_authorization(actor_user)

        stmt = select(IdeaReviewRecord).where(IdeaReviewRecord.idea_id == idea_id)
        record = (await db.execute(stmt)).scalars().first()
        if not record:
            record = await self.sync_idea_review_record(db, idea_id)

        prev_status = record.review_status
        record.assigned_reviewer_id = reviewer_user_id
        record.review_status = ReviewStatus.UNDER_REVIEW.value

        action = IdeaReviewAction(
            review_record_id=record.id,
            actor_user_id=actor_user.user_id,
            action_type=ReviewActionType.ASSIGN.value,
            previous_status=prev_status,
            new_status=record.review_status,
            reviewer_comments=f"Assigned reviewer: {reviewer_user_id}",
        )
        db.add(action)
        await db.commit()
        await db.refresh(record)
        return record

    async def perform_review_action(
        self,
        db: AsyncSession,
        idea_id: str,
        actor_user: UserSession,
        action_type: str,
        comments: Optional[str] = None,
        override_rationale: Optional[str] = None,
        target_decision_state: Optional[str] = None,
    ) -> IdeaReviewRecord:
        """
        Executes review action with strict audit trails and immutable override preservation.
        """
        self._check_reviewer_authorization(actor_user)

        stmt = (
            select(IdeaReviewRecord)
            .where(IdeaReviewRecord.idea_id == idea_id)
            .options(selectinload(IdeaReviewRecord.idea))
        )
        record = (await db.execute(stmt)).scalars().first()
        if not record:
            record = await self.sync_idea_review_record(db, idea_id)

        idea = record.idea
        prev_status = record.review_status
        now = datetime.now(timezone.utc)

        # 1. State Machine Transition & Validation
        if action_type == ReviewActionType.APPROVE.value:
            if record.review_status == ReviewStatus.APPROVED.value:
                raise ValueError("Review is already in APPROVED status (Duplicate action).")
            record.review_status = ReviewStatus.APPROVED.value
            record.final_decision = "APPROVED"
            record.final_decision_by = actor_user.user_id
            record.final_decision_at = now
            record.final_decision_reason = comments
            if idea:
                idea.decision_state = IdeaDecisionState.ACCEPTED_FOR_STUDY.value

        elif action_type == ReviewActionType.REJECT.value:
            if record.review_status == ReviewStatus.REJECTED.value:
                raise ValueError("Review is already in REJECTED status (Duplicate action).")
            record.review_status = ReviewStatus.REJECTED.value
            record.final_decision = "REJECTED"
            record.final_decision_by = actor_user.user_id
            record.final_decision_at = now
            record.final_decision_reason = comments
            if idea:
                idea.decision_state = IdeaDecisionState.REJECTED.value

        elif action_type == ReviewActionType.OVERRIDE.value:
            if not override_rationale:
                raise ValueError("Override requires an explicit override_rationale.")
            record.review_status = ReviewStatus.OVERRIDDEN.value
            record.final_decision = f"OVERRIDDEN_{target_decision_state or 'MODIFIED'}"
            record.final_decision_by = actor_user.user_id
            record.final_decision_at = now
            record.final_decision_reason = override_rationale
            if idea and target_decision_state:
                idea.decision_state = target_decision_state

        elif action_type == ReviewActionType.ESCALATE.value:
            record.review_status = ReviewStatus.ESCALATED.value
            record.is_escalated = True

        elif action_type == ReviewActionType.REQUEST_MORE_EVIDENCE.value:
            record.review_status = ReviewStatus.MORE_EVIDENCE_REQUESTED.value

        elif action_type == ReviewActionType.REOPEN.value:
            record.review_status = ReviewStatus.PENDING_REVIEW.value
            record.final_decision = None
            record.final_decision_by = None
            record.final_decision_at = None

        else:
            raise ValueError(f"Unknown review action type: {action_type}")

        # 2. Persist Immutable Review Action Audit
        action = IdeaReviewAction(
            review_record_id=record.id,
            actor_user_id=actor_user.user_id,
            action_type=action_type,
            previous_status=prev_status,
            new_status=record.review_status,
            reviewer_comments=comments,
            override_rationale=override_rationale,
            action_metadata={
                "calibrated_confidence": record.calibrated_confidence_score,
                "original_automated_decision": record.original_automated_decision,
                "original_evidence_state": record.original_evidence_state,
            },
        )
        db.add(action)

        # 3. Persist General Audit Log
        audit = AuditLog(
            user_id=actor_user.user_id,
            action=f"GOVERNANCE_REVIEW_{action_type}",
            entity_type="IdeaReviewRecord",
            entity_id=record.id,
            decision=record.final_decision,
            override_reason=override_rationale or comments,
            metadata_json={
                "idea_id": idea_id,
                "previous_status": prev_status,
                "new_status": record.review_status,
                "is_safety_critical": record.is_safety_critical,
                "confidence_tier": record.confidence_tier,
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(record)
        return record

    def _check_reviewer_authorization(self, user: UserSession):
        """Verifies that the actor user has cost engineering or governance review privileges."""
        user_roles = set(r.upper() for r in user.roles)
        if not (user_roles & self.ALLOWED_REVIEWER_ROLES):
            raise PermissionError(
                f"User {user.username} lacks required reviewer role. Required: {self.ALLOWED_REVIEWER_ROLES}"
            )
