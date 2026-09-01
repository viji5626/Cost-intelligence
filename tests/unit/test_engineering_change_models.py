"""
Unit Tests for Engineering Changes (ECN) and Implementation Tracking Models
"""

from database.models.engineering_change import (
    EngineeringChange,
    Implementation,
)


def test_engineering_change_instantiation():
    ecn = EngineeringChange(
        id="ecn-01",
        ecn_number="ECN-2024-ENG-089",
        title="Optimization of Rear Swingarm Bush Material",
        release_date="2024-03-15",
        status="RELEASED",
        change_category="COST_REDUCTION",
        estimated_saving_per_veh=3.50,
        source_system="PLM_TEAMCENTER",
    )
    assert ecn.ecn_number == "ECN-2024-ENG-089"
    assert ecn.estimated_saving_per_veh == 3.50
    assert ecn.status == "RELEASED"


def test_implementation_7_state_taxonomy():
    imp = Implementation(
        id="imp-01",
        engineering_change_id="ecn-01",
        part_id="prt-01",
        plant_id="plt-haridwar",
        model_year_id="my-01",
        status="IMPLEMENTATION_CONFIRMED",
        implementation_date="2024-05-01",
        cutoff_chassis_number="MBH44A999P800100",
        verification_source="SAP_MES_CUTOFF",
        confidence_score=0.98,
    )
    assert imp.status == "IMPLEMENTATION_CONFIRMED"
    assert imp.confidence_score == 0.98
    assert imp.cutoff_chassis_number == "MBH44A999P800100"
