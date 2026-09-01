"""
Deterministic Vehicle Cost Opportunity Engine
Implements strict mathematical formulas for vehicle idea financial opportunity valuation.
"""

from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from database.models.ideathon import OpportunityStatus


def to_decimal(val: Optional[float | int | Decimal | str]) -> Optional[Decimal]:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except Exception:
        return None


class OpportunityCalculationResult(BaseModel):
    """Output of deterministic vehicle cost opportunity valuation."""

    status: str = OpportunityStatus.CALCULATED.value
    current_piece_cost_inr: Optional[float] = None
    proposed_piece_cost_inr: Optional[float] = None
    saving_per_vehicle_inr: Optional[float] = None

    applicable_annual_volume: int = 0
    gross_annual_opportunity_inr: Optional[float] = None
    tooling_investment_inr: float = 0.0
    validation_investment_inr: float = 0.0
    net_opportunity_inr: Optional[float] = None

    payback_period_years: Optional[float] = None
    payback_period_months: Optional[float] = None

    applicable_models: List[str] = Field(default_factory=list)
    volume_by_model: Dict[str, int] = Field(default_factory=dict)
    effective_model_year: Optional[str] = None
    formula_version: str = "V1.0_DETERMINISTIC"
    provenance_hash: str = ""
    provenance_metadata: Dict = Field(default_factory=dict)


class VehicleOpportunityEngine:
    """
    Deterministic mathematical calculation engine for vehicle cost reductions.
    Strictly forbids LLM arithmetic. Employs Decimal arithmetic for financial integrity.
    """

    FORMULA_VERSION = "V1.0_DETERMINISTIC"

    @classmethod
    def calculate_opportunity(
        cls,
        current_piece_cost: Optional[float | Decimal],
        proposed_piece_cost: Optional[float | Decimal],
        volumes_by_model: Dict[str, int],
        applicable_model_codes: List[str],
        tooling_investment: float | Decimal = 0.0,
        validation_investment: float | Decimal = 0.0,
        effective_calendar_year: Optional[int] = None,
        model_year_calendar_years: Optional[Dict[str, int]] = None,
        raw_claimed_saving: Optional[float | Decimal] = None,
    ) -> OpportunityCalculationResult:
        """
        Executes deterministic opportunity calculation with strict edge case handling.
        """
        dec_current = to_decimal(current_piece_cost)
        dec_proposed = to_decimal(proposed_piece_cost)
        dec_claimed = to_decimal(raw_claimed_saving)
        dec_tooling = to_decimal(tooling_investment) or Decimal("0.0")
        dec_validation = to_decimal(validation_investment) or Decimal("0.0")

        # 1. Filter Applicable Volumes based on applicable models and effective dates
        filtered_volume_by_model: Dict[str, int] = {}
        total_volume = 0

        for model_code in applicable_model_codes:
            # Check calendar year filtering if specified
            if effective_calendar_year is not None and model_year_calendar_years:
                model_cal_year = model_year_calendar_years.get(model_code)
                if model_cal_year is not None and model_cal_year < effective_calendar_year:
                    # Exclude past/ineffective model years
                    continue

            vol = volumes_by_model.get(model_code, 0)
            if vol > 0:
                filtered_volume_by_model[model_code] = vol
                total_volume += vol

        # 2. Check Missing Baseline Cost
        if dec_current is None:
            # If current piece cost is missing from BOM
            provenance_dict = {
                "formula_version": cls.FORMULA_VERSION,
                "current_cost": None,
                "proposed_cost": float(dec_proposed) if dec_proposed else None,
                "total_volume": total_volume,
                "status": OpportunityStatus.MISSING_BOM_COST.value,
            }
            p_hash = cls._compute_provenance_hash(provenance_dict)

            return OpportunityCalculationResult(
                status=OpportunityStatus.MISSING_BOM_COST.value,
                current_piece_cost_inr=None,
                proposed_piece_cost_inr=float(dec_proposed) if dec_proposed else None,
                saving_per_vehicle_inr=None,
                applicable_annual_volume=total_volume,
                applicable_models=applicable_model_codes,
                volume_by_model=filtered_volume_by_model,
                tooling_investment_inr=float(dec_tooling),
                validation_investment_inr=float(dec_validation),
                formula_version=cls.FORMULA_VERSION,
                provenance_hash=p_hash,
                provenance_metadata=provenance_dict,
            )

        # 3. Check Proposed Cost or Claimed Saving
        if dec_proposed is None:
            if dec_claimed is not None and dec_claimed > Decimal("0.0"):
                # Derive proposed cost = current - claimed
                dec_proposed = dec_current - dec_claimed
            else:
                provenance_dict = {
                    "formula_version": cls.FORMULA_VERSION,
                    "current_cost": float(dec_current),
                    "proposed_cost": None,
                    "total_volume": total_volume,
                    "status": OpportunityStatus.UNQUANTIFIED.value,
                }
                p_hash = cls._compute_provenance_hash(provenance_dict)

                return OpportunityCalculationResult(
                    status=OpportunityStatus.UNQUANTIFIED.value,
                    current_piece_cost_inr=float(dec_current),
                    proposed_piece_cost_inr=None,
                    saving_per_vehicle_inr=None,
                    applicable_annual_volume=total_volume,
                    applicable_models=applicable_model_codes,
                    volume_by_model=filtered_volume_by_model,
                    tooling_investment_inr=float(dec_tooling),
                    validation_investment_inr=float(dec_validation),
                    formula_version=cls.FORMULA_VERSION,
                    provenance_hash=p_hash,
                    provenance_metadata=provenance_dict,
                )

        # 4. Compute Saving Per Vehicle
        dec_saving_per_veh = (dec_current - dec_proposed).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # 5. Check Negative or Zero Saving
        if dec_saving_per_veh < Decimal("0.0"):
            status = OpportunityStatus.NEGATIVE_SAVING.value
        elif dec_saving_per_veh == Decimal("0.0"):
            status = OpportunityStatus.NO_OPPORTUNITY.value
        elif total_volume == 0:
            status = OpportunityStatus.INSUFFICIENT_VOLUME_DATA.value
        else:
            status = OpportunityStatus.CALCULATED.value

        # 6. Compute Financial Opportunities
        dec_gross_annual = (dec_saving_per_veh * Decimal(total_volume)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        total_investment = dec_tooling + dec_validation
        dec_net_opportunity = (dec_gross_annual - total_investment).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        # 7. Compute Payback Period
        payback_years: Optional[float] = None
        payback_months: Optional[float] = None

        if total_investment == Decimal("0.0"):
            if dec_gross_annual > Decimal("0.0"):
                payback_years = 0.0
                payback_months = 0.0
        elif dec_gross_annual > Decimal("0.0"):
            dec_pb = total_investment / dec_gross_annual
            payback_years = round(float(dec_pb), 4)
            payback_months = round(float(dec_pb * Decimal("12.0")), 2)

        # 8. Construct Provenance Hash & Metadata
        provenance_dict = {
            "formula_version": cls.FORMULA_VERSION,
            "current_piece_cost_inr": float(dec_current),
            "proposed_piece_cost_inr": float(dec_proposed),
            "saving_per_vehicle_inr": float(dec_saving_per_veh),
            "applicable_annual_volume": total_volume,
            "volume_by_model": filtered_volume_by_model,
            "gross_annual_opportunity_inr": float(dec_gross_annual),
            "tooling_investment_inr": float(dec_tooling),
            "validation_investment_inr": float(dec_validation),
            "net_opportunity_inr": float(dec_net_opportunity),
            "payback_period_years": payback_years,
            "status": status,
        }
        p_hash = cls._compute_provenance_hash(provenance_dict)

        return OpportunityCalculationResult(
            status=status,
            current_piece_cost_inr=float(dec_current),
            proposed_piece_cost_inr=float(dec_proposed),
            saving_per_vehicle_inr=float(dec_saving_per_veh),
            applicable_annual_volume=total_volume,
            gross_annual_opportunity_inr=float(dec_gross_annual),
            tooling_investment_inr=float(dec_tooling),
            validation_investment_inr=float(dec_validation),
            net_opportunity_inr=float(dec_net_opportunity),
            payback_period_years=payback_years,
            payback_period_months=payback_months,
            applicable_models=applicable_model_codes,
            volume_by_model=filtered_volume_by_model,
            effective_model_year=str(effective_calendar_year) if effective_calendar_year else None,
            formula_version=cls.FORMULA_VERSION,
            provenance_hash=p_hash,
            provenance_metadata=provenance_dict,
        )

    @staticmethod
    def _compute_provenance_hash(data: dict) -> str:
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
