"""
Deterministic Unit Normalization and Date Parsing Service
"""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional, Tuple, Union


class UnitNormalizer:
    """Provides pure deterministic unit normalization without floating point drift."""

    @staticmethod
    def parse_decimal(value: Any) -> Optional[Decimal]:
        """Safely parses strings, floats, ints, or currency formatted strings into Decimal."""
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))

        s = str(value).strip()
        if not s:
            return None

        # Remove currency symbols, commas, and whitespace
        s = s.replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").replace("$", "").strip()

        try:
            return Decimal(s)
        except InvalidOperation:
            return None

    @staticmethod
    def parse_date(value: Any) -> Optional[date]:
        """Parses dates from various formats (ISO, DD/MM/YYYY, DD-MM-YYYY, Excel serial numbers)."""
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()

        if isinstance(value, (int, float)):
            # Excel serial date offset (Excel base date is Dec 30, 1899)
            try:
                serial = float(value)
                if 20000 < serial < 60000:
                    dt = datetime.fromordinal(datetime(1899, 12, 30).toordinal() + int(serial))
                    return dt.date()
            except Exception:
                pass

        s = str(value).strip()
        if not s:
            return None

        # Try standard formats
        formats = [
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y/%m/%d",
            "%d.%m.%Y",
            "%b-%Y",
            "%B %Y",
            "%Y-%m",
        ]
        for fmt in formats:
            try:
                dt = datetime.strptime(s, fmt)
                return dt.date()
            except ValueError:
                continue

        return None

    @staticmethod
    def normalize_currency_unit(value: Decimal, unit_hint: Optional[str] = None) -> Tuple[Decimal, str]:
        """
        Normalizes currency expressions (Lakhs, Crores, Millions) into exact Rupees (INR).
        Returns (normalized_rupees, detected_unit).
        """
        hint = (unit_hint or "").lower().strip()

        if "cr" in hint or "crore" in hint:
            return value * Decimal("10000000"), "CRORES"
        if "lakh" in hint or "lac" in hint or "lacs" in hint or "lakhs" in hint:
            return value * Decimal("100000"), "LAKHS"
        if "million" in hint or "mn" in hint:
            return value * Decimal("1000000"), "MILLIONS"
        if "k" in hint or "thousand" in hint:
            return value * Decimal("1000"), "THOUSANDS"

        return value, "INR"

    @staticmethod
    def normalize_energy_kwh(value: Decimal, unit_hint: Optional[str] = None) -> Tuple[Decimal, str]:
        """
        Normalizes electrical energy into standard kilowatt-hours (kWh).
        """
        hint = (unit_hint or "").lower().strip()

        if "mwh" in hint:
            return value * Decimal("1000"), "MWH"
        if "gwh" in hint:
            return value * Decimal("1000000"), "GWH"
        if "mj" in hint:
            # 1 kWh = 3.6 MJ
            return value / Decimal("3.6"), "MJ"

        return value, "KWH"

    @staticmethod
    def normalize_water_kl(value: Decimal, unit_hint: Optional[str] = None) -> Tuple[Decimal, str]:
        """
        Normalizes liquid volume into standard kiloliters (KL) / cubic meters (m³).
        """
        hint = (unit_hint or "").lower().strip()

        if "liter" in hint or "litre" in hint or "l" == hint:
            return value / Decimal("1000"), "LITERS"
        if "m3" in hint or "cu.m" in hint or "cum" in hint:
            return value, "M3"  # 1 m³ = 1 KL

        return value, "KL"
