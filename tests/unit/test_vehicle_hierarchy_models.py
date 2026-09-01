"""
Unit Tests for Vehicle Hierarchy Relational Models
"""

from database.models.vehicle_hierarchy import (
    ProductFamily,
    Vehicle,
    VehicleModel,
    VehicleVariant,
    ModelGeneration,
    ModelYear,
)


def test_product_family_instantiation():
    pf = ProductFamily(
        family_code="FAM-COMMUTER-100",
        name="Economy 100cc Commuter Family",
        description="High volume mass commuter motorcycles",
        is_active=True,
    )
    assert pf.family_code == "FAM-COMMUTER-100"
    assert pf.name == "Economy 100cc Commuter Family"
    assert pf.is_active is True


def test_vehicle_hierarchy_relationships():
    pf = ProductFamily(id="fam-01", family_code="FAM-01", name="Commuter")
    veh = Vehicle(id="veh-01", vehicle_code="VEH-SPL", name="Splendor", product_family_id=pf.id, product_family=pf)
    model = VehicleModel(id="mod-01", model_code="MOD-SPL-PLUS", name="Splendor+", vehicle_id=veh.id, vehicle=veh)
    variant = VehicleVariant(id="var-01", variant_code="VAR-DRUM", name="Drum Cast", model_id=model.id, model=model, displacement_cc=97.2)
    gen = ModelGeneration(id="gen-01", generation_code="GEN-BS6", name="BS6 Phase 2", variant_id=variant.id, variant=variant, start_year=2023)
    my = ModelYear(id="my-01", year_code="MY2024-SPL", generation_id=gen.id, generation=gen, calendar_year=2024, annual_volume_planned=450000)

    assert my.calendar_year == 2024
    assert my.annual_volume_planned == 450000
    assert my.generation.variant.model.vehicle.product_family.name == "Commuter"
    assert my.generation.variant.displacement_cc == 97.2
