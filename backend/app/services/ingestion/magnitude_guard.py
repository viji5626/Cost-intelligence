"""
Magnitude Anomaly Guard
Detects scale confusion (Rupee vs Lakh, kWh vs MWh), unit mismatches, and domain outliers.
Distinguishes between INVALID_DATA (rejected) and UNUSUAL_VALID_DATA (accepted with warning).
"""

from decimal import Decimal
from typing import Any, Dict, List, Tuple
from backend.app.services.ingestion.models import ValidationSeverity


class MagnitudeAnomalyGuard:
    """Statistical and domain bounds sanity guard for automotive and plant operations."""

    # Typical automotive operational bounds (per vehicle produced or per part)
    BOUNDS = {
        "plant_opex": {
            # Total OPEX per vehicle produced (₹/veh)
            "opex_per_veh_min": Decimal("200.00"),
            "opex_per_veh_max": Decimal("3500.00"),
            "opex_per_veh_unusual_high": Decimal("1500.00"),
            # Electrical energy per vehicle produced (kWh/veh)
            "kwh_per_veh_min": Decimal("8.00"),
            "kwh_per_veh_max": Decimal("85.00"),
            "kwh_per_veh_unusual_high": Decimal("45.00"),
            # Water consumption per vehicle produced (KL/veh)
            "kl_per_veh_min": Decimal("0.05"),
            "kl_per_veh_max": Decimal("1.50"),
            "kl_per_veh_unusual_high": Decimal("0.60"),
        },
        "component_cost": {
            # Standard single 2-wheeler component piece price (₹)
            "piece_price_min": Decimal("0.10"),
            "piece_price_max": Decimal("35000.00"),  # Complete engine / frame / ABS kit
            "piece_price_unusual_high": Decimal("15000.00"),
        },
        "bom_item": {
            # Usage quantity per vehicle
            "qty_min": Decimal("0.0001"),
            "qty_max": Decimal("250.00"),  # Fasteners, spokes, ball bearings
            "qty_unusual_high": Decimal("80.00"),
        },
        "engineering_change": {
            # Expected savings per vehicle (₹/veh)
            "saving_min": Decimal("0.01"),
            "saving_max": Decimal("1500.00"),
            "saving_unusual_high": Decimal("250.00"),
        },
    }

    @classmethod
    def validate_plant_opex_row(cls, data: Dict[str, Any]) -> Tuple[ValidationSeverity, List[str], List[str]]:
        """
        Validates a single Plant OPEX row against domain operational envelopes.
        Returns (severity, errors, warnings).
        """
        errors: List[str] = []
        warnings: List[str] = []

        prod_qty = data.get("production_quantity")
        total_opex = data.get("total_opex")
        electricity_kwh = data.get("electricity_kwh")
        water_kl = data.get("water_kl")

        if prod_qty is None or prod_qty <= 0:
            errors.append(f"Invalid production_quantity: {prod_qty}. Must be > 0.")
            return ValidationSeverity.INVALID_DATA, errors, warnings

        if total_opex is None or total_opex < 0:
            errors.append(f"Invalid total_opex: {total_opex}. Cannot be negative.")
            return ValidationSeverity.INVALID_DATA, errors, warnings

        # Derived KPI checks
        prod_dec = Decimal(str(prod_qty))
        opex_per_veh = total_opex / prod_dec
        b = cls.BOUNDS["plant_opex"]

        # Check for Rupee vs Lakh confusion (e.g. user entered total in Lakhs instead of ₹)
        if opex_per_veh < Decimal("10.00"):
            errors.append(
                f"Scale Anomaly: OPEX per vehicle is ₹{opex_per_veh:.2f}, which indicates total_opex was likely entered in Lakhs/Crores rather than Rupees."
            )
            return ValidationSeverity.INVALID_DATA, errors, warnings

        if opex_per_veh > (b["opex_per_veh_max"] * Decimal("10.0")):
            errors.append(
                f"Extreme Outlier: OPEX per vehicle is ₹{opex_per_veh:.2f} (> 10x max limit ₹{b['opex_per_veh_max']})."
            )
            return ValidationSeverity.INVALID_DATA, errors, warnings

        if opex_per_veh > b["opex_per_veh_unusual_high"]:
            warnings.append(
                f"High Operational Variance: OPEX per vehicle is ₹{opex_per_veh:.2f} (above typical ₹{b['opex_per_veh_unusual_high']})."
            )

        # Check electricity consumption per vehicle
        if electricity_kwh is not None and electricity_kwh > 0:
            kwh_per_veh = electricity_kwh / prod_dec
            if kwh_per_veh < Decimal("1.00"):
                errors.append(
                    f"Scale Anomaly: Electricity is {kwh_per_veh:.2f} kWh/veh (likely entered in MWh or thousand kWh)."
                )
                return ValidationSeverity.INVALID_DATA, errors, warnings

            if kwh_per_veh > (b["kwh_per_veh_max"] * Decimal("5.0")):
                errors.append(
                    f"Extreme Energy Anomaly: {kwh_per_veh:.2f} kWh/veh exceeds physical plant boundaries."
                )
                return ValidationSeverity.INVALID_DATA, errors, warnings

            if kwh_per_veh > b["kwh_per_veh_unusual_high"]:
                warnings.append(
                    f"Elevated Energy Intensity: {kwh_per_veh:.2f} kWh/veh (typical benchmark < {b['kwh_per_veh_unusual_high']})."
                )

        # Check water consumption per vehicle
        if water_kl is not None and water_kl > 0:
            kl_per_veh = water_kl / prod_dec
            if kl_per_veh > b["kl_per_veh_max"] * Decimal("5.0"):
                errors.append(f"Extreme Water Anomaly: {kl_per_veh:.2f} KL/veh exceeds physical limit.")
                return ValidationSeverity.INVALID_DATA, errors, warnings
            if kl_per_veh > b["kl_per_veh_unusual_high"]:
                warnings.append(f"Elevated Water Intensity: {kl_per_veh:.2f} KL/veh.")

        if warnings:
            return ValidationSeverity.UNUSUAL_VALID_DATA, errors, warnings

        return ValidationSeverity.VALID, errors, warnings

    @classmethod
    def validate_component_cost_row(cls, data: Dict[str, Any]) -> Tuple[ValidationSeverity, List[str], List[str]]:
        """Validates component cost breakdown."""
        errors: List[str] = []
        warnings: List[str] = []

        total_cost = data.get("total_cost")
        rm_cost = data.get("raw_material_cost", Decimal("0.0"))
        proc_cost = data.get("process_cost", Decimal("0.0"))
        oh_cost = data.get("overhead_cost", Decimal("0.0"))
        tool_cost = data.get("tool_amortization", Decimal("0.0"))

        if total_cost is None or total_cost <= Decimal("0.0"):
            errors.append(f"Invalid total_cost: {total_cost}. Must be > 0.")
            return ValidationSeverity.INVALID_DATA, errors, warnings

        b = cls.BOUNDS["component_cost"]
        if total_cost > b["piece_price_max"]:
            errors.append(
                f"Extreme Price Outlier: Total cost ₹{total_cost} exceeds single component maximum (₹{b['piece_price_max']}). Likely scale error."
            )
            return ValidationSeverity.INVALID_DATA, errors, warnings

        # Sum sanity check
        calculated_sum = rm_cost + proc_cost + oh_cost + tool_cost
        if calculated_sum > Decimal("0.0"):
            diff = abs(total_cost - calculated_sum)
            if diff > Decimal("1.00") and (diff / total_cost) > Decimal("0.05"):
                warnings.append(
                    f"Cost Sum Discrepancy: Component total ₹{total_cost} differs from sub-elements sum ₹{calculated_sum} by ₹{diff}."
                )

        if total_cost > b["piece_price_unusual_high"]:
            warnings.append(f"High-Value Component: Piece price ₹{total_cost} is in the top 5th percentile.")

        if warnings:
            return ValidationSeverity.UNUSUAL_VALID_DATA, errors, warnings

        return ValidationSeverity.VALID, errors, warnings

    @classmethod
    def validate_bom_item_row(cls, data: Dict[str, Any]) -> Tuple[ValidationSeverity, List[str], List[str]]:
        """Validates BOM item usage quantity."""
        errors: List[str] = []
        warnings: List[str] = []

        qty = data.get("quantity_per_vehicle")
        if qty is None or qty <= Decimal("0.0"):
            errors.append(f"Invalid BOM quantity: {qty}. Must be > 0.")
            return ValidationSeverity.INVALID_DATA, errors, warnings

        b = cls.BOUNDS["bom_item"]
        if qty > b["qty_max"]:
            errors.append(f"Excessive BOM Quantity: {qty} per vehicle exceeds max limit ({b['qty_max']}).")
            return ValidationSeverity.INVALID_DATA, errors, warnings

        if qty > b["qty_unusual_high"]:
            warnings.append(f"High Component Quantity: {qty} parts per vehicle.")

        if warnings:
            return ValidationSeverity.UNUSUAL_VALID_DATA, errors, warnings

        return ValidationSeverity.VALID, errors, warnings
