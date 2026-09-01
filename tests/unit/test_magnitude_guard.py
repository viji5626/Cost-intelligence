"""
Unit Tests for Magnitude Anomaly Guard
"""

from decimal import Decimal
from backend.app.services.ingestion.magnitude_guard import MagnitudeAnomalyGuard
from backend.app.services.ingestion.models import ValidationSeverity


def test_magnitude_guard_valid_opex():
    row = {
        "production_quantity": 100000,
        "total_opex": Decimal("50000000.00"),  # ₹500/vehicle (within standard range 200 - 3500)
        "electricity_kwh": Decimal("2500000.00"),  # 25 kWh/vehicle (within 8 - 85)
        "water_kl": Decimal("20000.00"),  # 0.20 KL/vehicle (within 0.05 - 1.5)
    }
    severity, errors, warnings = MagnitudeAnomalyGuard.validate_plant_opex_row(row)
    assert severity == ValidationSeverity.VALID
    assert len(errors) == 0
    assert len(warnings) == 0


def test_magnitude_guard_scale_confusion_lakhs_vs_rupees():
    row = {
        "production_quantity": 100000,
        "total_opex": Decimal("500.00"),  # User entered "500" thinking Lakhs, resulting in ₹0.005/vehicle!
        "electricity_kwh": Decimal("2500000.00"),
    }
    severity, errors, warnings = MagnitudeAnomalyGuard.validate_plant_opex_row(row)
    assert severity == ValidationSeverity.INVALID_DATA
    assert len(errors) >= 1
    assert "Scale Anomaly" in errors[0]


def test_magnitude_guard_unusual_valid_opex():
    row = {
        "production_quantity": 100000,
        "total_opex": Decimal("180000000.00"),  # ₹1,800/vehicle (unusual high but plausible, e.g. low-volume EV ramp)
        "electricity_kwh": Decimal("5500000.00"),  # 55 kWh/vehicle (elevated)
    }
    severity, errors, warnings = MagnitudeAnomalyGuard.validate_plant_opex_row(row)
    assert severity == ValidationSeverity.UNUSUAL_VALID_DATA
    assert len(errors) == 0
    assert len(warnings) >= 1


def test_magnitude_guard_component_cost():
    valid_part = {"total_cost": Decimal("450.00")}
    s1, _, _ = MagnitudeAnomalyGuard.validate_component_cost_row(valid_part)
    assert s1 == ValidationSeverity.VALID

    # ₹5,00,000 for a single bracket -> Invalid scale error
    invalid_part = {"total_cost": Decimal("500000.00")}
    s2, errors, _ = MagnitudeAnomalyGuard.validate_component_cost_row(invalid_part)
    assert s2 == ValidationSeverity.INVALID_DATA
    assert len(errors) >= 1
