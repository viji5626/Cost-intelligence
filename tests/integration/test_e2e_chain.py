"""
Phase 10 — E2E Business-Chain Integration Test (LEVEL 1)
=========================================================
Tests the complete data flow:
  MASTER DATA → OPEX KPI → BENCHMARK → IDEATHON → HYBRID RETRIEVAL →
  DISCOVERY → APPLICABILITY → OPPORTUNITY → GOVERNANCE → REVIEW ACTION → CONSOLIDATION

Test database: sqlite+aiosqlite:///:memory:  (same pattern as all 17 existing tests)
No PostgreSQL required. Included in standard pytest suite.
"""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from backend.app.core.database import Base
from backend.app.core.security import UserSession
from backend.app.services.discovery.discovery_service import DiscoveryService
from backend.app.services.governance.governance_service import GovernanceService
from backend.app.services.ideathon.ideathon_service import IdeathonService
from backend.app.services.opportunity.opportunity_service import OpportunityService
from backend.app.services.opex.opex_service import PlantOpexService
from calculations.opex.models import BenchmarkMode
from database.models.auth import User
from database.models.governance import (
    IdeaReviewAction,
    IdeaReviewRecord,
    ReviewActionType,
    ReviewStatus,
)
from database.models.ideathon import (
    IdeaSubmission,
    ImplementationEvidenceState,
)
from database.models.part_bom import Assembly, Component, ComponentCost, Part, Subsystem
from database.models.plant_opex import OpexRecord, Plant
from database.models.vehicle_hierarchy import (
    ModelGeneration,
    ModelYear,
    ProductFamily,
    Vehicle,
    VehicleModel,
    VehicleVariant,
)


# ---------------------------------------------------------------------------
# Shared fixture: full in-memory schema + demo seed data
# ---------------------------------------------------------------------------

@pytest.fixture
async def chain_session():
    """
    Creates an in-memory SQLite database seeded with all master data required
    for the 12-step E2E business chain test.

    Entity IDs use -DEMO suffix to clearly distinguish from any production identifiers.
    All records use source_system='SYNTHETIC_DEMO' where the field exists.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:

        # ── STEP 1 SEED: Master Data ───────────────────────────────────────

        user = User(
            id="user-demo-01",
            email="cost.engineer@hero-demo.com",
            username="engineer_demo",
            hashed_password="SYNTHETIC_DEMO_HASH",
            full_name="Demo Cost Engineer",
            role="COST_ENGINEER",
            is_active=True,
        )

        pf = ProductFamily(id="pf-demo-100", family_code="MOTORCYCLES_100CC_DEMO", name="100cc Motorcycles DEMO")
        veh = Vehicle(id="veh-demo-spl", vehicle_code="SPLENDOR_DEMO", name="Splendor DEMO", product_family_id="pf-demo-100")
        mod = VehicleModel(id="mod-demo-spl", model_code="SPLENDOR_PLUS_DEMO", name="Splendor Plus DEMO", vehicle_id="veh-demo-spl")
        var = VehicleVariant(id="var-demo-spl", variant_code="SPL_DRUM_DEMO", name="Splendor Plus Drum DEMO", model_id="mod-demo-spl")
        gen = ModelGeneration(id="gen-demo-spl", generation_code="SPL_G1_DEMO", name="Gen 1 DEMO", variant_id="var-demo-spl", start_year=2022)
        my = ModelYear(
            id="my-demo-spl",
            year_code="SPL_2024_DEMO",
            generation_id="gen-demo-spl",
            calendar_year=2024,
            annual_volume_planned=1_000_000,
        )

        sub = Subsystem(id="sub-demo-brk", code="BRAKE_SYSTEM_DEMO", name="Brake System DEMO")
        assy = Assembly(id="assy-demo-brk", subsystem_id="sub-demo-brk", code="DRUM_BRAKE_DEMO", name="Drum Brake DEMO")
        comp = Component(id="comp-demo-brk", assembly_id="assy-demo-brk", code="BRAKE_LEVER_DEMO", name="Brake Lever DEMO")
        part = Part(
            id="part-demo-brk",
            component_id="comp-demo-brk",
            part_number="53100-DEMO-001",
            part_name="Front Brake Lever DEMO",
            is_safety_critical=False,
        )
        cost_rec = ComponentCost(
            id="cost-demo-brk",
            part_id="part-demo-brk",
            period_start=date(2024, 1, 1),
            raw_material_cost=28.00,
            process_cost=8.50,
            overhead_cost=4.50,
            tool_amortization=1.50,
            total_cost=42.50,       # ₹42.50 total piece cost
            currency="INR",
            source_system="SYNTHETIC_DEMO",
        )

        plant_a = Plant(
            id="plant-a-demo",
            plant_code="PLANT-A-DEMO",
            name="Plant A Demo (Haridwar)",
            location="Haridwar",
            state="UK",
            annual_capacity_vehicles=1_200_000,
            manufacturing_scope="FULL_VEHICLE_ASSEMBLY",
            grid_tariff_inr_kwh=Decimal("7.50"),
        )
        plant_b = Plant(
            id="plant-b-demo",
            plant_code="PLANT-B-DEMO",
            name="Plant B Demo (Dharuhera)",
            location="Dharuhera",
            state="HR",
            annual_capacity_vehicles=1_200_000,
            manufacturing_scope="FULL_VEHICLE_ASSEMBLY",
            grid_tariff_inr_kwh=Decimal("7.40"),
        )

        session.add_all([user, pf, veh, mod, var, gen, my, sub, assy, comp, part, cost_rec, plant_a, plant_b])
        await session.flush()

        # ── STEP 2 SEED: OPEX Records ──────────────────────────────────────

        opex_a = OpexRecord(
            plant_id="plant-a-demo",
            period=date(2024, 4, 1),
            production_quantity=100_000,
            electricity_kwh=Decimal("4250000.00"),
            electricity_cost=Decimal("31875000.00"),
            water_kl=Decimal("35000.00"),
            water_cost=Decimal("875000.00"),
            gas_consumption_nm3=Decimal("120000.00"),
            gas_cost=Decimal("5000000.00"),
            compressed_air_nm3=Decimal("345000.00"),
            compressed_air_cost=Decimal("1520000.00"),
            is_compressor_power_embedded=True,
            waste_quantity_mt=Decimal("150.00"),
            waste_cost=Decimal("600000.00"),
            labor_cost=Decimal("20000000.00"),
            maintenance_cost=Decimal("10000000.00"),
            other_opex=Decimal("4200000.00"),
            total_opex=Decimal("59500000.00"),
        )
        opex_b = OpexRecord(
            plant_id="plant-b-demo",
            period=date(2024, 4, 1),
            production_quantity=95_000,
            electricity_kwh=Decimal("3610000.00"),
            electricity_cost=Decimal("26714000.00"),
            water_kl=Decimal("29000.00"),
            water_cost=Decimal("754000.00"),
            gas_consumption_nm3=Decimal("100000.00"),
            gas_cost=Decimal("4000000.00"),
            compressed_air_nm3=Decimal("275500.00"),
            compressed_air_cost=Decimal("1235000.00"),
            is_compressor_power_embedded=True,
            waste_quantity_mt=Decimal("140.00"),
            waste_cost=Decimal("560000.00"),
            labor_cost=Decimal("17000000.00"),
            maintenance_cost=Decimal("8000000.00"),
            other_opex=Decimal("3100000.00"),
            total_opex=Decimal("49400000.00"),
        )
        session.add_all([opex_a, opex_b])
        await session.commit()

        yield session

    await engine.dispose()


# ---------------------------------------------------------------------------
# Individual STEP tests (1–6)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_step1_master_data_entities_persisted(chain_session: AsyncSession):
    """STEP 1 — Master data seeded correctly with expected IDs and codes."""
    plant_a = (await chain_session.execute(select(Plant).where(Plant.id == "plant-a-demo"))).scalars().first()
    plant_b = (await chain_session.execute(select(Plant).where(Plant.id == "plant-b-demo"))).scalars().first()
    part = (await chain_session.execute(select(Part).where(Part.id == "part-demo-brk"))).scalars().first()
    my = (await chain_session.execute(select(ModelYear).where(ModelYear.id == "my-demo-spl"))).scalars().first()

    assert plant_a is not None, "Plant-A-DEMO must be seeded"
    assert plant_b is not None, "Plant-B-DEMO must be seeded"
    assert plant_a.plant_code == "PLANT-A-DEMO"
    assert plant_b.plant_code == "PLANT-B-DEMO"
    assert part is not None, "Demo brake part must be seeded"
    assert part.part_number == "53100-DEMO-001"
    assert my is not None
    assert my.annual_volume_planned == 1_000_000


@pytest.mark.asyncio
async def test_step2_opex_double_count_guard(chain_session: AsyncSession):
    """STEP 2 — OPEX records persisted with is_compressor_power_embedded=True."""
    rec_a = (await chain_session.execute(
        select(OpexRecord).where(OpexRecord.plant_id == "plant-a-demo")
    )).scalars().first()
    assert rec_a is not None
    assert rec_a.is_compressor_power_embedded is True, "Double-count guard must be True on Plant-A"
    assert rec_a.production_quantity == 100_000
    assert rec_a.total_opex == Decimal("59500000.00")


@pytest.mark.asyncio
async def test_step3_opex_kpi_calculation(chain_session: AsyncSession):
    """STEP 3 — KPI engine calculates per-vehicle metrics for Plant-A."""
    kpis = await PlantOpexService.get_plant_kpis_for_period(chain_session, "plant-a-demo", "2024-04-01")
    assert kpis is not None
    assert kpis.kwh_per_vehicle > 0, "kwh_per_vehicle must be positive"
    assert kpis.water_kl_per_vehicle > 0
    assert kpis.total_opex_per_vehicle > 0
    assert 580 < float(kpis.total_opex_per_vehicle) < 620, (
        f"Expected ~₹595/veh, got: {kpis.total_opex_per_vehicle}"
    )
    if kpis.compressed_air:
        assert kpis.compressed_air.is_compressor_power_embedded is True


@pytest.mark.asyncio
async def test_step4_benchmark_auto_selection(chain_session: AsyncSession):
    """STEP 4 — Backend auto-selects Plant-B as best comparable peer (no benchmark_plant_id input)."""
    result = await PlantOpexService.run_benchmark_analysis(
        session=chain_session,
        target_plant_id="plant-a-demo",
        period_str="2024-04-01",
        mode=BenchmarkMode.BEST_COMPARABLE,
        # NOTE: benchmark_plant_id is NOT passed — backend owns peer selection
    )
    assert result is not None, "Benchmark result must not be None"
    assert result.gross_annual_opportunity_inr is not None
    assert float(result.gross_annual_opportunity_inr) > 0, (
        "Gross annual opportunity must be positive — Plant-A OPEX > Plant-B OPEX"
    )
    assert "Best Comparable Peer" in result.benchmark_source_name, (
        f"Expected 'Best Comparable Peer' in benchmark_source_name, got: '{result.benchmark_source_name}'"
    )


@pytest.mark.asyncio
async def test_step5_ideathon_submission(chain_session: AsyncSession):
    """STEP 5 — Idea normalized and persisted with UUID and submission_code."""
    idea = await IdeathonService.submit_and_normalize_idea(
        session=chain_session,
        title="Replace Front Brake Lever Alloy with Glass-Filled Polymer — Splendor",
        description="Replace 53100-DEMO-001 brake lever alloy with polymer composite. "
                    "Saves ₹8.50 per vehicle. Applicable to Splendor Plus DEMO family.",
        submitter_employee_id="EMP-DEMO-001",
        submitter_plant_code="PLANT-A-DEMO",
        raw_claimed_saving=8.50,
    )
    assert idea is not None
    assert idea.id is not None and len(idea.id) > 0, "idea.id (UUID) must be set"
    assert idea.submission_code.startswith("IDEA-"), (
        f"submission_code must start with 'IDEA-', got: {idea.submission_code}"
    )
    assert idea.evidence_state == ImplementationEvidenceState.NOT_EVALUATED.value


@pytest.mark.asyncio
async def test_step6_hybrid_retrieval_no_exception(chain_session: AsyncSession):
    """STEP 6 — Hybrid retrieval (MockAIProvider) completes without exception."""
    from backend.app.services.retrieval.retrieval_service import RetrievalService

    svc = RetrievalService()
    # search() takes raw_query as positional; RetrievalQuery class does not exist — use kwargs
    results = await svc.search(
        chain_session,
        raw_query="brake lever polymer substitution cost reduction",
        entity_type_filter="part",
        top_k=5,
    )
    assert isinstance(results, list), "Retrieval must return a list (may be empty without seeded embeddings)"


# ---------------------------------------------------------------------------
# STEPS 7–12: Full sequential chain (maintains idea_id across all steps)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_steps_7_to_12_full_chain_sequential(chain_session: AsyncSession):
    """
    STEPS 7–12 — Sequential chain preserving idea_id end-to-end.
    Runs: discovery → applicability → opportunity → governance sync → review action → consolidation.
    """
    # Submit idea
    idea = await IdeathonService.submit_and_normalize_idea(
        session=chain_session,
        title="Polymer Composite Brake Lever — CHAIN TEST — Splendor",
        description="Replace 53100-DEMO-001 from die-cast alloy to polymer composite. "
                    "Saving ₹8.50/vehicle. Applicable to Splendor Plus DEMO.",
        submitter_employee_id="EMP-DEMO-CHAIN-01",
        submitter_plant_code="PLANT-A-DEMO",
        raw_claimed_saving=8.50,
    )
    idea_id = idea.id
    assert idea_id, "idea_id must be a non-empty UUID"

    # ── STEP 7: Evidence Discovery ──────────────────────────────────────────
    discovery_svc = DiscoveryService()
    evidence_result = await discovery_svc.evaluate_idea_implementation_evidence(
        session=chain_session,
        idea_id=idea_id,
    )
    assert evidence_result is not None

    refreshed_idea = (await chain_session.execute(
        select(IdeaSubmission).where(IdeaSubmission.id == idea_id)
    )).scalars().first()
    assert refreshed_idea is not None
    assert refreshed_idea.id == idea_id, "idea.id must be unchanged after discovery (ID chain integrity)"
    assert refreshed_idea.evidence_state is not None

    # ── STEP 8: Applicability ───────────────────────────────────────────────
    from backend.app.services.applicability.applicability_engine import ApplicabilityMatrixEngine
    # get_cross_model_summary is the actual API — evaluate_for_idea does not exist
    applicability = await ApplicabilityMatrixEngine.get_cross_model_summary(
        session=chain_session,
        part_number="53100-DEMO-001",
    )
    # No BomItem seeded → returns None (acceptable — the method must not raise)
    assert applicability is None or hasattr(applicability, "part_id"), (
        "get_cross_model_summary must return None or CrossModelApplicabilitySummary"
    )

    # ── STEP 9: Opportunity Calculation ─────────────────────────────────────
    opp_svc = OpportunityService()
    opp_result = await opp_svc.evaluate_idea_opportunity(
        db=chain_session,
        idea_id=idea_id,
        tooling_investment=0.0,
        validation_investment=0.0,
    )
    assert opp_result is not None
    assert opp_result.status is not None

    # Terminology enforcement: "npv" must NOT appear in any field name
    result_fields = opp_result.model_dump().keys()
    npv_fields = [f for f in result_fields if "npv" in f.lower()]
    assert not npv_fields, f"Forbidden 'npv' field(s) found: {npv_fields}"

    # Payback fields must use correct terminology
    has_payback = hasattr(opp_result, "payback_period_years") or hasattr(opp_result, "payback_period_months")
    assert has_payback, "payback_period_years or payback_period_months must exist"
    assert opp_result.provenance_hash, "provenance_hash must be non-empty"
    provenance_hash = opp_result.provenance_hash

    # ── STEP 10: Governance Sync ─────────────────────────────────────────────
    gov_svc = GovernanceService()
    review_record = await gov_svc.sync_idea_review_record(chain_session, idea_id)
    assert review_record.idea_id == idea_id
    assert review_record.calibrated_confidence_score is not None
    assert review_record.confidence_tier is not None
    assert review_record.review_priority is not None

    # ── STEP 11: Review Action ────────────────────────────────────────────────
    actor = UserSession(user_id="user-demo-01", username="engineer_demo", roles=["COST_ENGINEER"], is_active=True)
    updated_record = await gov_svc.perform_review_action(
        db=chain_session,
        idea_id=idea_id,
        actor_user=actor,
        action_type=ReviewActionType.APPROVE.value,
        comments="SYNTHETIC_DEMO: Approved for feasibility study.",
    )
    assert updated_record.review_status == ReviewStatus.APPROVED.value

    action_stmt = (
        select(IdeaReviewAction)
        .where(IdeaReviewAction.review_record_id == updated_record.id)
        .order_by(IdeaReviewAction.created_at.desc())
    )
    latest_action = (await chain_session.execute(action_stmt)).scalars().first()
    assert latest_action is not None
    assert latest_action.action_type == ReviewActionType.APPROVE.value
    assert latest_action.review_record_id == updated_record.id

    # ── STEP 12: Full Business Case Consolidation ─────────────────────────────
    chain_session.expire_all()
    consolidated_stmt = (
        select(IdeaSubmission)
        .where(IdeaSubmission.id == idea_id)
        .options(
            selectinload(IdeaSubmission.opportunity_evaluation),
            selectinload(IdeaSubmission.review_record).selectinload(IdeaReviewRecord.actions),
        )
    )
    full_idea = (await chain_session.execute(consolidated_stmt)).scalars().first()
    assert full_idea is not None

    # End-to-end UUID preservation
    assert full_idea.id == idea_id, "idea.id must equal the original UUID through all 12 steps"

    # Provenance hash stability
    if full_idea.opportunity_evaluation:
        assert full_idea.opportunity_evaluation.provenance_hash == provenance_hash, (
            "Provenance hash must be stable from Step 9 through Step 12"
        )

    # Review record traceability
    assert full_idea.review_record is not None
    assert full_idea.review_record.idea_id == idea_id

    final_action = sorted(full_idea.review_record.actions, key=lambda a: a.created_at)[-1]
    assert final_action.action_type == ReviewActionType.APPROVE.value, (
        "Last action must be APPROVE from Step 11"
    )
