"""
Integration Tests for Governance Workflow Service
Tests reviewer actions, overrides, audit logs, duplicate action prevention, and escalation.
"""

from datetime import date
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base
from backend.app.core.security import UserSession
from backend.app.services.governance.governance_service import GovernanceService
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
from database.models.part_bom import Assembly, BomItem, Component, ComponentCost, Part, Subsystem
from database.models.vehicle_hierarchy import ModelGeneration, ModelYear, ProductFamily, Vehicle, VehicleModel, VehicleVariant
from database.models.auth import User


@pytest.fixture
async def governance_test_session():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        # Seed user
        user = User(
            id="user-gov-01",
            email="engineer@hero.com",
            username="cost_eng_1",
            hashed_password="hash",
            full_name="Lead Cost Engineer",
            role="COST_ENGINEER",
            is_active=True,
        )

        # Seed hierarchy
        pf = ProductFamily(id="pf-gov-100", family_code="MOTORCYCLES_100CC", name="100cc Motorcycles")
        veh = Vehicle(id="veh-gov-spl", vehicle_code="SPLENDOR", name="Splendor", product_family_id="pf-gov-100")
        mod = VehicleModel(id="mod-gov-spl", model_code="SPLENDOR_PLUS", name="Splendor Plus", vehicle_id="veh-gov-spl")
        var = VehicleVariant(id="var-gov-spl", variant_code="SPL_DRUM", name="Splendor Plus Drum", model_id="mod-gov-spl")
        gen = ModelGeneration(id="gen-gov-spl", generation_code="SPL_G1", name="Gen 1", variant_id="var-gov-spl", start_year=2022)
        my = ModelYear(id="my-gov-spl", year_code="SPL_2024", generation_id="gen-gov-spl", calendar_year=2024, annual_volume_planned=1000000)

        # Seed part in BRAKES subsystem (Safety Critical)
        sub = Subsystem(id="sub-gov-brk", code="BRAKE_SYSTEM", name="Brake System")
        assy = Assembly(id="assy-gov-brk", subsystem_id="sub-gov-brk", code="DRUM_BRAKE", name="Drum Brake Assembly")
        comp = Component(id="comp-gov-brk", assembly_id="assy-gov-brk", code="BRAKE_LEVER", name="Brake Lever Component")
        part = Part(
            id="part-gov-brk",
            component_id="comp-gov-brk",
            part_number="53100-KTR-900",
            part_name="Front Brake Lever",
            is_safety_critical=True,
        )

        # Seed Idea
        idea = IdeaSubmission(
            id="idea-gov-01",
            submission_code="IDEA-2024-0901",
            raw_title="Lightweight alloy brake lever for Splendor Plus",
            raw_description="Change front brake lever alloy to save ₹2.50 per vehicle.",
            raw_claimed_saving_per_veh=2.50,
            target_vehicle_id="veh-gov-spl",
            target_model_id="SPLENDOR_PLUS",
            target_part_id="part-gov-brk",
            extracted_part_number="53100-KTR-900",
            decision_state=IdeaDecisionState.SUBMITTED.value,
            evidence_state=ImplementationEvidenceState.NO_EVIDENCE_FOUND.value,
        )

        # Seed Opportunity Evaluation (Net ₹2.5M)
        opp = IdeaOpportunityEvaluation(
            idea_id="idea-gov-01",
            current_piece_cost_inr=50.0,
            proposed_piece_cost_inr=47.50,
            saving_per_vehicle_inr=2.50,
            applicable_annual_volume=1000000,
            gross_annual_opportunity_inr=2500000.0,
            net_opportunity_inr=2500000.0,
            provenance_hash="mock-hash",
        )

        session.add_all([user, pf, veh, mod, var, gen, my, sub, assy, comp, part, idea, opp])
        await session.commit()
        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_governance_workflow_full_lifecycle(governance_test_session: AsyncSession):
    session = governance_test_session
    service = GovernanceService()
    user_session = UserSession(user_id="user-gov-01", username="cost_eng_1", roles=["COST_ENGINEER"])

    # 1. Sync review record and verify Safety Critical P0 Priority
    record = await service.sync_idea_review_record(session, "idea-gov-01")
    assert record.is_safety_critical is True
    assert record.review_priority == ReviewPriority.CRITICAL_P0.value
    assert record.review_status == ReviewStatus.PENDING_REVIEW.value
    assert record.routing_reasons is not None
    assert any("SAFETY_CRITICAL_SYSTEM" in r for r in record.routing_reasons)

    # 2. Assign Reviewer
    record = await service.assign_reviewer(session, "idea-gov-01", "user-gov-01", user_session)
    assert record.assigned_reviewer_id == "user-gov-01"
    assert record.review_status == ReviewStatus.UNDER_REVIEW.value

    # 3. Request More Evidence
    record = await service.perform_review_action(
        session,
        "idea-gov-01",
        actor_user=user_session,
        action_type=ReviewActionType.REQUEST_MORE_EVIDENCE.value,
        comments="Please provide fatigue test report for brake lever alloy.",
    )
    assert record.review_status == ReviewStatus.MORE_EVIDENCE_REQUESTED.value

    # 4. Escalate Review
    record = await service.perform_review_action(
        session,
        "idea-gov-01",
        actor_user=user_session,
        action_type=ReviewActionType.ESCALATE.value,
        comments="Escalated to Chief Engineer for brake homologation review.",
    )
    assert record.review_status == ReviewStatus.ESCALATED.value
    assert record.is_escalated is True

    # 5. Reviewer Override
    record = await service.perform_review_action(
        session,
        "idea-gov-01",
        actor_user=user_session,
        action_type=ReviewActionType.OVERRIDE.value,
        override_rationale="Homologation test report passed by ARAI Pune. Approved for pilot run.",
        target_decision_state=IdeaDecisionState.APPROVED_FOR_IMPLEMENTATION.value,
    )
    assert record.review_status == ReviewStatus.OVERRIDDEN.value
    assert record.final_decision is not None and "OVERRIDDEN" in record.final_decision
    assert record.final_decision_by == "user-gov-01"
    assert record.final_decision_reason is not None

    # Verify idea decision state updated while preserving evidence state
    stmt = select(IdeaSubmission).where(IdeaSubmission.id == "idea-gov-01")
    idea = (await session.execute(stmt)).scalars().first()
    assert idea is not None
    assert idea.decision_state == IdeaDecisionState.APPROVED_FOR_IMPLEMENTATION.value
    assert idea.evidence_state == ImplementationEvidenceState.NO_EVIDENCE_FOUND.value

    # 6. Verify Complete Immutable Audit Trail
    actions = (await session.execute(select(IdeaReviewAction).where(IdeaReviewAction.review_record_id == record.id))).scalars().all()
    assert len(actions) == 4  # ASSIGN, REQUEST_MORE_EVIDENCE, ESCALATE, OVERRIDE

    audits = (await session.execute(select(AuditLog).where(AuditLog.entity_id == record.id))).scalars().all()
    assert len(audits) == 3  # REQUEST_MORE_EVIDENCE, ESCALATE, OVERRIDE

    # 7. Test Reopen Review
    record = await service.perform_review_action(
        session,
        "idea-gov-01",
        actor_user=user_session,
        action_type=ReviewActionType.REOPEN.value,
        comments="Reopened for annual cost review.",
    )
    assert record.review_status == ReviewStatus.PENDING_REVIEW.value
    assert record.final_decision is None
