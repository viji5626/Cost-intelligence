"""
Unit Tests for Deterministic Vehicle Cost Opportunity Engine
Validates all 14 required synthetic scenarios and exact financial arithmetic.
"""

from decimal import Decimal
import pytest
from backend.app.services.opportunity.opportunity_engine import VehicleOpportunityEngine
from database.models.ideathon import OpportunityStatus


def test_scenario_1_positive_saving():
    """Scenario 1: Positive saving per vehicle (e.g. Current ₹120, Proposed ₹116.50 -> ₹3.50 saving)."""
    res = VehicleOpportunityEngine.calculate_opportunity(
        current_piece_cost=120.0,
        proposed_piece_cost=116.50,
        volumes_by_model={"SPLENDOR_PLUS": 1000000},
        applicable_model_codes=["SPLENDOR_PLUS"],
        tooling_investment=0.0,
        validation_investment=0.0,
    )

    assert res.status == OpportunityStatus.CALCULATED.value
    assert res.saving_per_vehicle_inr == 3.50
    assert res.applicable_annual_volume == 1000000
    assert res.gross_annual_opportunity_inr == 3500000.0
    assert res.net_opportunity_inr == 3500000.0
    assert res.payback_period_years == 0.0
    assert len(res.provenance_hash) == 64


def test_scenario_2_zero_saving():
    """Scenario 2: Zero saving (Current ₹50, Proposed ₹50)."""
    res = VehicleOpportunityEngine.calculate_opportunity(
        current_piece_cost=50.0,
        proposed_piece_cost=50.0,
        volumes_by_model={"SPLENDOR_PLUS": 500000},
        applicable_model_codes=["SPLENDOR_PLUS"],
    )

    assert res.status == OpportunityStatus.NO_OPPORTUNITY.value
    assert res.saving_per_vehicle_inr == 0.0
    assert res.gross_annual_opportunity_inr == 0.0
    assert res.payback_period_years is None


def test_scenario_3_negative_saving():
    """Scenario 3: Negative saving (Proposed cost ₹55 exceeds current cost ₹50)."""
    res = VehicleOpportunityEngine.calculate_opportunity(
        current_piece_cost=50.0,
        proposed_piece_cost=55.0,
        volumes_by_model={"SPLENDOR_PLUS": 500000},
        applicable_model_codes=["SPLENDOR_PLUS"],
    )

    assert res.status == OpportunityStatus.NEGATIVE_SAVING.value
    assert res.saving_per_vehicle_inr == -5.0
    assert res.gross_annual_opportunity_inr == -2500000.0
    assert res.payback_period_years is None


def test_scenario_4_tooling_investment():
    """Scenario 4: Tooling investment payback period calculation."""
    # Saving ₹4.0/veh, Volume 500,000 -> Gross ₹2,000,000. Tooling ₹1,000,000 -> Payback 0.5 years (6 months)
    res = VehicleOpportunityEngine.calculate_opportunity(
        current_piece_cost=100.0,
        proposed_piece_cost=96.0,
        volumes_by_model={"HF_DELUXE": 500000},
        applicable_model_codes=["HF_DELUXE"],
        tooling_investment=1000000.0,
        validation_investment=0.0,
    )

    assert res.status == OpportunityStatus.CALCULATED.value
    assert res.gross_annual_opportunity_inr == 2000000.0
    assert res.tooling_investment_inr == 1000000.0
    assert res.net_opportunity_inr == 1000000.0
    assert res.payback_period_years == 0.5
    assert res.payback_period_months == 6.0


def test_scenario_5_validation_investment():
    """Scenario 5: Testing & validation investment included in payback."""
    # Saving ₹2.0/veh, Volume 500,000 -> Gross ₹1,000,000. Tooling ₹500,000, Validation ₹250,000 -> Total Inv ₹750,000 -> Payback 0.75 years (9 months)
    res = VehicleOpportunityEngine.calculate_opportunity(
        current_piece_cost=80.0,
        proposed_piece_cost=78.0,
        volumes_by_model={"GLAMOUR": 500000},
        applicable_model_codes=["GLAMOUR"],
        tooling_investment=500000.0,
        validation_investment=250000.0,
    )

    assert res.status == OpportunityStatus.CALCULATED.value
    assert res.gross_annual_opportunity_inr == 1000000.0
    assert res.net_opportunity_inr == 250000.0
    assert res.payback_period_years == 0.75
    assert res.payback_period_months == 9.0


def test_scenario_6_zero_production():
    """Scenario 6: Zero production volume available."""
    res = VehicleOpportunityEngine.calculate_opportunity(
        current_piece_cost=100.0,
        proposed_piece_cost=90.0,
        volumes_by_model={"OBSOLETE_MODEL": 0},
        applicable_model_codes=["OBSOLETE_MODEL"],
    )

    assert res.status == OpportunityStatus.INSUFFICIENT_VOLUME_DATA.value
    assert res.saving_per_vehicle_inr == 10.0
    assert res.applicable_annual_volume == 0
    assert res.gross_annual_opportunity_inr == 0.0


def test_scenario_7_missing_bom_cost():
    """Scenario 7: Base part cost missing in ERP/PLM BOM."""
    res = VehicleOpportunityEngine.calculate_opportunity(
        current_piece_cost=None,
        proposed_piece_cost=45.0,
        volumes_by_model={"SPLENDOR_PLUS": 800000},
        applicable_model_codes=["SPLENDOR_PLUS"],
    )

    assert res.status == OpportunityStatus.MISSING_BOM_COST.value
    assert res.current_piece_cost_inr is None
    assert res.saving_per_vehicle_inr is None
    assert res.gross_annual_opportunity_inr is None


def test_scenario_8_partial_model_applicability():
    """Scenario 8: Part shared across 3 models, but idea applicable to only 2."""
    volumes = {
        "SPLENDOR_PLUS": 1000000,
        "HF_DELUXE": 600000,
        "PASSION_PLUS": 400000,
    }
    # Idea applies only to SPLENDOR_PLUS and HF_DELUXE
    res = VehicleOpportunityEngine.calculate_opportunity(
        current_piece_cost=200.0,
        proposed_piece_cost=195.0,  # ₹5 saving
        volumes_by_model=volumes,
        applicable_model_codes=["SPLENDOR_PLUS", "HF_DELUXE"],
    )

    assert res.status == OpportunityStatus.CALCULATED.value
    assert res.saving_per_vehicle_inr == 5.0
    assert res.applicable_annual_volume == 1600000  # 1M + 600k (excludes 400k Passion+)
    assert res.gross_annual_opportunity_inr == 8000000.0


def test_scenario_9_historical_implementation_valuation():
    """Scenario 9: Claimed saving when idea already implemented in past."""
    # When already implemented, can calculate theoretical gross opportunity achieved
    res = VehicleOpportunityEngine.calculate_opportunity(
        current_piece_cost=150.0,
        proposed_piece_cost=142.0,
        volumes_by_model={"SPLENDOR_PLUS": 1200000},
        applicable_model_codes=["SPLENDOR_PLUS"],
    )

    assert res.status == OpportunityStatus.CALCULATED.value
    assert res.saving_per_vehicle_inr == 8.0
    assert res.gross_annual_opportunity_inr == 9600000.0


def test_scenario_10_future_effective_date_applicability():
    """Scenario 10: Idea applicable from MY2027 onward -> exclude MY2025/MY2026."""
    volumes = {
        "SPL_2025": 1000000,
        "SPL_2026": 1100000,
        "SPL_2027": 1200000,
    }
    model_years = {
        "SPL_2025": 2025,
        "SPL_2026": 2026,
        "SPL_2027": 2027,
    }

    res = VehicleOpportunityEngine.calculate_opportunity(
        current_piece_cost=50.0,
        proposed_piece_cost=47.0,
        volumes_by_model=volumes,
        applicable_model_codes=["SPL_2025", "SPL_2026", "SPL_2027"],
        effective_calendar_year=2027,
        model_year_calendar_years=model_years,
    )

    assert res.status == OpportunityStatus.CALCULATED.value
    assert res.applicable_annual_volume == 1200000  # Excluded 2025 and 2026
    assert res.gross_annual_opportunity_inr == 3600000.0


def test_scenario_11_cost_change_over_time():
    """Scenario 11: Claimed saving specified directly instead of explicit proposed cost."""
    res = VehicleOpportunityEngine.calculate_opportunity(
        current_piece_cost=300.0,
        proposed_piece_cost=None,
        raw_claimed_saving=12.50,
        volumes_by_model={"MAVERICK_440": 50000},
        applicable_model_codes=["MAVERICK_440"],
    )

    assert res.status == OpportunityStatus.CALCULATED.value
    assert res.proposed_piece_cost_inr == 287.50
    assert res.saving_per_vehicle_inr == 12.50
    assert res.gross_annual_opportunity_inr == 625000.0


def test_scenario_12_large_volume_opportunity():
    """Scenario 12: High-volume mass market platform (e.g. 2.5 million units)."""
    res = VehicleOpportunityEngine.calculate_opportunity(
        current_piece_cost=25.0,
        proposed_piece_cost=24.10,  # ₹0.90 saving
        volumes_by_model={"SPLENDOR_HERO_FLEET": 2500000},
        applicable_model_codes=["SPLENDOR_HERO_FLEET"],
        tooling_investment=450000.0,
    )

    assert res.status == OpportunityStatus.CALCULATED.value
    assert res.saving_per_vehicle_inr == 0.90
    assert res.gross_annual_opportunity_inr == 2250000.0
    assert res.net_opportunity_inr == 1800000.0
    assert res.payback_period_years == 0.2  # 2.4 months


def test_scenario_13_small_volume_opportunity():
    """Scenario 13: Premium low volume platform (e.g. Karizma XMR 15,000 units)."""
    res = VehicleOpportunityEngine.calculate_opportunity(
        current_piece_cost=1500.0,
        proposed_piece_cost=1420.0,  # ₹80 saving
        volumes_by_model={"KARIZMA_XMR": 15000},
        applicable_model_codes=["KARIZMA_XMR"],
        tooling_investment=200000.0,
    )

    assert res.status == OpportunityStatus.CALCULATED.value
    assert res.saving_per_vehicle_inr == 80.0
    assert res.gross_annual_opportunity_inr == 1200000.0
    assert res.net_opportunity_inr == 1000000.0


def test_scenario_14_decimal_rounding_precision():
    """Scenario 14: Fractional paisa and decimal precision edge cases."""
    # Current ₹12.3333, Proposed ₹11.2111 -> Saving ₹1.1222 on 333,333 units
    res = VehicleOpportunityEngine.calculate_opportunity(
        current_piece_cost=12.3333,
        proposed_piece_cost=11.2111,
        volumes_by_model={"TEST_MODEL": 333333},
        applicable_model_codes=["TEST_MODEL"],
    )

    assert res.status == OpportunityStatus.CALCULATED.value
    assert res.saving_per_vehicle_inr == 1.1222
    # 1.1222 * 333333 = 374066.2926
    assert res.gross_annual_opportunity_inr == 374066.2926
