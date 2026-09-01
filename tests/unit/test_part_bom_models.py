"""
Unit Tests for Subsystem, Assembly, Component, Part, Material, Supplier, and BOM Models
"""

from database.models.part_bom import (
    Subsystem,
    Assembly,
    Component,
    Material,
    Supplier,
    Part,
    BomItem,
    ComponentCost,
)


def test_engineering_breakdown_lineage():
    sub = Subsystem(id="sub-01", code="SUB-CHASSIS", name="Frame and Chassis", is_safety_critical=True)
    asm = Assembly(id="asm-01", code="ASM-SWINGARM", name="Rear Swingarm Assembly", subsystem_id=sub.id, subsystem=sub, is_safety_critical=True)
    comp = Component(id="comp-01", code="COMP-BUSH", name="Swingarm Pivot Bush", assembly_id=asm.id, assembly=asm, is_safety_critical=True)
    mat = Material(id="mat-01", material_code="MAT-EN8", name="Carbon Steel EN8", material_category="METALLIC", base_rate_per_kg=78.50)
    part = Part(
        id="prt-01",
        part_number="52101KCC900",
        part_name="BUSH, SWINGARM PIVOT",
        component_id=comp.id,
        component=comp,
        material_id=mat.id,
        material=mat,
        weight_kg=0.185,
        is_safety_critical=True,
    )

    assert part.part_number == "52101KCC900"
    assert part.component.assembly.subsystem.name == "Frame and Chassis"
    assert part.material.name == "Carbon Steel EN8"
    assert part.is_safety_critical is True


def test_bom_and_cost_models():
    bom = BomItem(
        id="bom-01",
        model_year_id="my-01",
        part_id="prt-01",
        quantity_per_vehicle=2.0,
        is_active=True,
    )
    cost = ComponentCost(
        id="cst-01",
        part_id="prt-01",
        period_start="2024-04-01",
        raw_material_cost=42.50,
        process_cost=15.20,
        overhead_cost=6.30,
        tool_amortization=2.00,
        total_cost=66.00,
        currency="INR",
        source_system="ERP_SAP",
    )

    assert bom.quantity_per_vehicle == 2.0
    assert cost.total_cost == 66.00
    assert cost.currency == "INR"
