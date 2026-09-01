"""
Integration Tests for Opportunity Valuation Service
"""

from datetime import date
from decimal import Decimal
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from backend.app.core.database import Base
from backend.app.services.opportunity.opportunity_service import OpportunityService
from database.models.ideathon import IdeaOpportunityEvaluation, IdeaSubmission, OpportunityStatus
from database.models.part_bom import Assembly, BomItem, Component, ComponentCost, Part, Subsystem
from database.models.vehicle_hierarchy import ModelGeneration, ModelYear, ProductFamily, Vehicle, VehicleModel, VehicleVariant


@pytest.fixture
async def opportunity_test_session():
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        # 1. Seed Product Family & Vehicle Lineage
        pf = ProductFamily(id="pf-opp-100", family_code="MOTORCYCLES_100CC", name="100cc Motorcycles")
        veh = Vehicle(id="veh-opp-spl", vehicle_code="SPLENDOR", name="Splendor", product_family_id="pf-opp-100")
        mod = VehicleModel(id="mod-opp-spl", model_code="SPLENDOR_PLUS", name="Splendor Plus", vehicle_id="veh-opp-spl")
        var = VehicleVariant(id="var-opp-spl", variant_code="SPL_DRUM", name="Splendor Plus Drum", model_id="mod-opp-spl")
        gen = ModelGeneration(id="gen-opp-spl", generation_code="SPL_G1", name="Gen 1", variant_id="var-opp-spl", start_year=2022)
        my = ModelYear(id="my-opp-spl", year_code="SPL_2024", generation_id="gen-opp-spl", calendar_year=2024, annual_volume_planned=1200000)

        # 2. Seed Sibling Vehicle HF Deluxe
        veh2 = Vehicle(id="veh-opp-hf", vehicle_code="HF", name="HF", product_family_id="pf-opp-100")
        mod2 = VehicleModel(id="mod-opp-hf", model_code="HF_DELUXE", name="HF Deluxe", vehicle_id="veh-opp-hf")
        var2 = VehicleVariant(id="var-opp-hf", variant_code="HF_STD", name="HF Deluxe Std", model_id="mod-opp-hf")
        gen2 = ModelGeneration(id="gen-opp-hf", generation_code="HF_G1", name="Gen 1", variant_id="var-opp-hf", start_year=2022)
        my2 = ModelYear(id="my-opp-hf", year_code="HF_2024", generation_id="gen-opp-hf", calendar_year=2024, annual_volume_planned=800000)

        # 3. Seed Component Breakdown & Part
        sub = Subsystem(id="sub-opp-eng", code="ENGINE", name="Engine")
        assy = Assembly(id="assy-opp-head", subsystem_id="sub-opp-eng", code="CYLINDER_HEAD", name="Cylinder Head Assembly")
        comp = Component(id="comp-opp-head", assembly_id="assy-opp-head", code="CYL_HEAD_COVER", name="Cylinder Head Cover Component")
        part = Part(id="part-opp-head", component_id="comp-opp-head", part_number="11100-KCC-900", part_name="Cylinder Head Cover")
        
        # Map part to both Splendor and HF Deluxe BOMs
        bom1 = BomItem(id="bom-opp-01", model_year_id="my-opp-spl", part_id="part-opp-head", quantity_per_vehicle=1.0)
        bom2 = BomItem(id="bom-opp-02", model_year_id="my-opp-hf", part_id="part-opp-head", quantity_per_vehicle=1.0)

        # 4. Seed Current Component Cost in ERP/PLM
        cost = ComponentCost(
            id="cost-opp-01",
            part_id="part-opp-head",
            period_start=date(2024, 1, 1),
            raw_material_cost=70.0,
            process_cost=30.0,
            overhead_cost=15.0,
            tool_amortization=5.0,
            total_cost=120.0,
            currency="INR",
        )

        # 5. Seed Idea Submission with Claimed Saving
        idea = IdeaSubmission(
            id="idea-opp-01",
            submission_code="IDEA-2024-0701",
            raw_title="Reduce wall thickness of Cylinder Head Cover",
            raw_description="Reduce wall thickness by 0.7mm to achieve ₹3.50 saving per vehicle.",
            raw_claimed_saving_per_veh=3.50,
            target_vehicle_id="veh-opp-spl",
            target_model_id="SPLENDOR_PLUS",
            target_part_id="part-opp-head",
            extracted_part_number="11100-KCC-900",
            decision_state="ACCEPTED_FOR_STUDY",
        )

        session.add_all([pf, veh, mod, var, gen, my, veh2, mod2, var2, gen2, my2, sub, assy, comp, part, bom1, bom2, cost, idea])
        await session.commit()
        yield session

    await test_engine.dispose()


@pytest.mark.asyncio
async def test_evaluate_idea_opportunity_service(opportunity_test_session: AsyncSession):
    session = opportunity_test_session
    service = OpportunityService()

    result = await service.evaluate_idea_opportunity(
        db=session,
        idea_id="idea-opp-01",
        tooling_investment=500000.0,
        validation_investment=200000.0,
    )

    assert result.status == OpportunityStatus.CALCULATED.value
    assert result.current_piece_cost_inr == 120.0
    assert result.proposed_piece_cost_inr == 116.50
    assert result.saving_per_vehicle_inr == 3.50
    # Total volume: 1.2M (Splendor) + 800k (HF Deluxe sharing part) = 2,000,000 units
    assert result.applicable_annual_volume == 2000000
    # Gross Opportunity: ₹3.50 * 2,000,000 = ₹7,000,000
    assert result.gross_annual_opportunity_inr == 7000000.0
    # Net Opportunity: ₹7,000,000 - ₹700,000 (500k + 200k) = ₹6,300,000
    assert result.net_opportunity_inr == 6300000.0
    # Payback: 700,000 / 7,000,000 = 0.1 years (1.2 months)
    assert result.payback_period_years == 0.1
    assert result.payback_period_months == 1.2
    assert len(result.provenance_hash) == 64

    # Verify persisted in database
    stmt = select(IdeaOpportunityEvaluation).where(IdeaOpportunityEvaluation.idea_id == "idea-opp-01")
    eval_row = (await session.execute(stmt)).scalars().first()
    assert eval_row is not None
    assert eval_row.gross_annual_opportunity_inr is not None
    assert eval_row.net_opportunity_inr is not None
    assert float(eval_row.gross_annual_opportunity_inr) == 7000000.0
    assert float(eval_row.net_opportunity_inr) == 6300000.0
