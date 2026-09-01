"""
Unit Tests for Unit Normalizer and Date Parser
"""

from datetime import date
from decimal import Decimal
from backend.app.services.ingestion.unit_normalizer import UnitNormalizer


def test_parse_decimal():
    assert UnitNormalizer.parse_decimal("1250.50") == Decimal("1250.50")
    assert UnitNormalizer.parse_decimal("₹ 1,450.00") == Decimal("1450.00")
    assert UnitNormalizer.parse_decimal("Rs. 50,000") == Decimal("50000")
    assert UnitNormalizer.parse_decimal(100) == Decimal("100")
    assert UnitNormalizer.parse_decimal(None) is None
    assert UnitNormalizer.parse_decimal("invalid_string") is None


def test_parse_date():
    assert UnitNormalizer.parse_date("2024-04-01") == date(2024, 4, 1)
    assert UnitNormalizer.parse_date("15/05/2024") == date(2024, 5, 15)
    assert UnitNormalizer.parse_date("01-04-2024") == date(2024, 4, 1)
    assert UnitNormalizer.parse_date(None) is None
    assert UnitNormalizer.parse_date("not-a-date") is None


def test_normalize_currency_units():
    val = Decimal("12.5")
    # Lakhs to Rupees: 12.5 * 100,000 = 1,250,000
    norm_lakhs, unit1 = UnitNormalizer.normalize_currency_unit(val, "Lakhs")
    assert norm_lakhs == Decimal("1250000")
    assert unit1 == "LAKHS"

    # Crores to Rupees: 2.5 * 10,000,000 = 25,000,000
    norm_crores, unit2 = UnitNormalizer.normalize_currency_unit(Decimal("2.5"), "Crores")
    assert norm_crores == Decimal("25000000")
    assert unit2 == "CRORES"


def test_normalize_energy_kwh():
    val = Decimal("4.2")
    # MWh to kWh: 4.2 * 1000 = 4200
    norm_mwh, unit = UnitNormalizer.normalize_energy_kwh(val, "MWh")
    assert norm_mwh == Decimal("4200")
    assert unit == "MWH"
