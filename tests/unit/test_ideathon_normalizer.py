"""
Unit Tests for Ideathon Normalizer and Entity Extraction
Validates wording variations, synonyms, ambiguity handling, categories, and duplicate scoring.
"""

from ai.ideathon.normalizer import IdeaNormalizer
from database.models.ideathon import CostReductionCategory, DataQualityStatus


def test_different_wording_same_idea():
    """Validates that different phrasing of the same engineering concept maps to identical canonical entities."""
    # Submission A
    res_a = IdeaNormalizer.normalize_submission(
        title="Reduce cylinder head cover thickness on Splendor Plus",
        description="Current head cover 11100-KCC-900 wall thickness is 3.5mm. Propose reducing to 2.8mm to save aluminum weight.",
    )
    # Submission B
    res_b = IdeaNormalizer.normalize_submission(
        title="Splendor+ valve cover wall thickness optimization",
        description="Problem: High weight of cylinder head cover. Solution: Downsize thickness of 11100-KCC-900 by 0.7mm.",
    )

    assert res_a.extracted_vehicle_alias == "SPLENDOR_PLUS"
    assert res_b.extracted_vehicle_alias == "SPLENDOR_PLUS"
    assert res_a.extracted_part_number == "11100-KCC-900"
    assert res_b.extracted_part_number == "11100-KCC-900"
    assert res_a.cost_reduction_category == CostReductionCategory.GEOMETRY_OPTIMIZATION
    assert res_b.cost_reduction_category == CostReductionCategory.GEOMETRY_OPTIMIZATION
    assert res_a.data_quality == DataQualityStatus.COMPLETE
    assert res_b.data_quality == DataQualityStatus.COMPLETE


def test_similar_but_technically_different_ideas():
    """Validates that ideas on the same vehicle targeting different components are distinguished."""
    idea_head_cover = IdeaNormalizer.normalize_submission(
        title="Splendor Plus cylinder head cover thickness reduction",
        description="Optimize wall thickness on 11100-KCC-900.",
    )
    idea_handle_weight = IdeaNormalizer.normalize_submission(
        title="Splendor Plus handlebar weight reduction",
        description="Reduce weight of handle balancer end weight by 50 grams.",
    )

    assert idea_head_cover.extracted_vehicle_alias == "SPLENDOR_PLUS"
    assert idea_handle_weight.extracted_vehicle_alias == "SPLENDOR_PLUS"
    assert idea_head_cover.extracted_component_alias == "CYLINDER_HEAD_COVER"
    assert idea_handle_weight.extracted_component_alias == "HANDLEBAR_WEIGHT"

    # Verify duplicate similarity between them is low
    sim = IdeaNormalizer.calculate_idea_similarity(
        idea_head_cover.raw_title, idea_head_cover.raw_description,
        idea_handle_weight.raw_title, idea_handle_weight.raw_description
    )
    assert sim < 0.50


def test_alias_and_synonym_normalization():
    res = IdeaNormalizer.normalize_submission(
        title="HF-Deluxe eco center stand bracket simplification",
        description="Replace stand comp main fastener with snap fit clip.",
    )
    assert res.extracted_vehicle_alias == "HF_DELUXE"
    assert res.extracted_component_alias == "MAIN_STAND"
    assert res.cost_reduction_category == CostReductionCategory.FASTENER_CONSOLIDATION


def test_missing_vehicle_information_routes_to_ambiguous():
    """Idea mentions a component and drawing but specifies no vehicle model."""
    res = IdeaNormalizer.normalize_submission(
        title="Optimize piston pin machining cycle time",
        description="Eliminate secondary grinding on piston pin 13111-087-000 across lines.",
    )
    assert res.extracted_vehicle_alias is None
    assert res.extracted_part_number == "13111-087-000"
    assert res.data_quality == DataQualityStatus.AMBIGUOUS_VEHICLE
    assert res.extraction_confidence < 0.65


def test_missing_component_information_routes_to_ambiguous():
    """Idea mentions a vehicle but vague component description without drawing or part name."""
    res = IdeaNormalizer.normalize_submission(
        title="Cost reduction on Glamour 125",
        description="We should find ways to reduce material cost across the motorcycle body.",
    )
    assert res.extracted_vehicle_alias == "GLAMOUR"
    assert res.extracted_part_number is None
    assert res.extracted_component_alias is None
    assert res.data_quality == DataQualityStatus.AMBIGUOUS_COMPONENT


def test_malformed_submission():
    res = IdeaNormalizer.normalize_submission(
        title="Vague Idea",
        description="Short",
    )
    assert res.data_quality == DataQualityStatus.MISSING_DATA
    assert res.extraction_confidence < 0.30


def test_duplicate_similarity_scoring():
    title1 = "Reduce handlebar weight on Xpulse 200"
    desc1 = "Reduce handle balancer weight from 150g to 100g to save cost."
    title2 = "Xpulse 200 handle balancer weight optimization"
    desc2 = "Downsize handle balancer weight by 50g to save raw material cost."

    sim = IdeaNormalizer.calculate_idea_similarity(title1, desc1, title2, desc2)
    assert sim >= 0.50
