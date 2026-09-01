"""
Opportunity Valuation Service
Coordinates Part Cost, Production Volume, Applicability Matrix, and Deterministic Financial Valuation.
"""

from typing import Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from backend.app.services.applicability.applicability_engine import ApplicabilityMatrixEngine
from backend.app.services.opportunity.opportunity_engine import OpportunityCalculationResult, VehicleOpportunityEngine
from database.models.ideathon import IdeaOpportunityEvaluation, IdeaSubmission, OpportunityStatus
from database.models.part_bom import ComponentCost, Part
from database.models.vehicle_hierarchy import ModelYear, VehicleModel, VehicleVariant, ModelGeneration


class OpportunityService:
    """
    Service layer orchestrating deterministic vehicle cost valuation against relational database records.
    """

    async def evaluate_idea_opportunity(
        self,
        db: AsyncSession,
        idea_id: str,
        tooling_investment: float = 0.0,
        validation_investment: float = 0.0,
        effective_calendar_year: Optional[int] = None,
        override_proposed_cost: Optional[float] = None,
    ) -> OpportunityCalculationResult:
        """
        Calculates and persists deterministic opportunity valuation for an idea submission.
        """
        # 1. Fetch Idea with existing evaluation
        stmt = (
            select(IdeaSubmission)
            .where(IdeaSubmission.id == idea_id)
            .options(selectinload(IdeaSubmission.opportunity_evaluation))
        )
        idea = (await db.execute(stmt)).scalars().first()
        if not idea:
            raise ValueError(f"IdeaSubmission not found for ID: {idea_id}")

        # 2. Retrieve Target Part
        part: Optional[Part] = None
        if idea.target_part_id:
            part = (await db.execute(select(Part).where(Part.id == idea.target_part_id))).scalars().first()
        elif idea.extracted_part_number:
            part = (await db.execute(select(Part).where(Part.part_number == idea.extracted_part_number))).scalars().first()

        # 3. Retrieve Current Component Cost from BOM
        current_piece_cost: Optional[float] = None
        if part:
            cost_stmt = (
                select(ComponentCost)
                .where(ComponentCost.part_id == part.id)
                .order_by(ComponentCost.period_start.desc())
            )
            cost_record = (await db.execute(cost_stmt)).scalars().first()
            if cost_record:
                current_piece_cost = float(cost_record.total_cost)

        # 4. Determine Unique Applicable Vehicle Models
        target_model_identifiers: List[str] = []
        if idea.target_model_id:
            target_model_identifiers.append(idea.target_model_id)

        if part:
            cross_summary = await ApplicabilityMatrixEngine.get_cross_model_summary(db, part.part_number)
            for model_name in cross_summary.sibling_models_sharing_part:
                target_model_identifiers.append(model_name)

        matched_models: List[VehicleModel] = []
        if target_model_identifiers:
            models_stmt = select(VehicleModel).where(
                (VehicleModel.id.in_(target_model_identifiers))
                | (VehicleModel.model_code.in_(target_model_identifiers))
                | (VehicleModel.name.in_(target_model_identifiers))
            )
            matched_models = list((await db.execute(models_stmt)).scalars().all())

        applicable_model_codes: List[str] = [m.model_code for m in matched_models]
        if not applicable_model_codes and idea.target_model_id:
            applicable_model_codes = [idea.target_model_id]

        # 5. Retrieve Annual Planned Volumes by Model
        volumes_by_model: Dict[str, int] = {}
        model_year_cal_years: Dict[str, int] = {}

        for vm in matched_models:
            vol_stmt = (
                select(ModelYear)
                .join(ModelGeneration, ModelYear.generation_id == ModelGeneration.id)
                .join(VehicleVariant, ModelGeneration.variant_id == VehicleVariant.id)
                .where(
                    VehicleVariant.model_id == vm.id,
                    ModelYear.is_active == True,
                )
            )
            my_records = (await db.execute(vol_stmt)).scalars().all()
            for my in my_records:
                vol = my.annual_volume_planned or 0
                volumes_by_model[vm.model_code] = volumes_by_model.get(vm.model_code, 0) + vol
                model_year_cal_years[vm.model_code] = my.calendar_year

        # 6. Execute Deterministic Calculation Engine
        proposed_cost = override_proposed_cost
        calc_result = VehicleOpportunityEngine.calculate_opportunity(
            current_piece_cost=current_piece_cost,
            proposed_piece_cost=proposed_cost,
            volumes_by_model=volumes_by_model,
            applicable_model_codes=applicable_model_codes,
            tooling_investment=tooling_investment,
            validation_investment=validation_investment,
            effective_calendar_year=effective_calendar_year,
            model_year_calendar_years=model_year_cal_years,
            raw_claimed_saving=float(idea.raw_claimed_saving_per_veh) if idea.raw_claimed_saving_per_veh else None,
        )

        # 7. Persist Evaluation to Database
        eval_record = idea.opportunity_evaluation
        if not eval_record:
            eval_record = IdeaOpportunityEvaluation(idea_id=idea.id, provenance_hash="")
            db.add(eval_record)

        eval_record.status = calc_result.status
        eval_record.current_piece_cost_inr = calc_result.current_piece_cost_inr
        eval_record.proposed_piece_cost_inr = calc_result.proposed_piece_cost_inr
        eval_record.saving_per_vehicle_inr = calc_result.saving_per_vehicle_inr
        eval_record.applicable_annual_volume = calc_result.applicable_annual_volume
        eval_record.gross_annual_opportunity_inr = calc_result.gross_annual_opportunity_inr
        eval_record.tooling_investment_inr = calc_result.tooling_investment_inr
        eval_record.validation_investment_inr = calc_result.validation_investment_inr
        eval_record.net_opportunity_inr = calc_result.net_opportunity_inr
        eval_record.payback_period_years = calc_result.payback_period_years
        eval_record.payback_period_months = calc_result.payback_period_months
        eval_record.applicable_models = calc_result.applicable_models
        eval_record.volume_by_model = calc_result.volume_by_model
        eval_record.effective_model_year = calc_result.effective_model_year
        eval_record.formula_version = calc_result.formula_version
        eval_record.provenance_hash = calc_result.provenance_hash
        eval_record.provenance_metadata = calc_result.provenance_metadata

        await db.commit()
        return calc_result
