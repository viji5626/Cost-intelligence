"""
Phase AI-08 Comprehensive Test Suite: Context Management & Token Budgeter
Tests explicit token budgeting, exact/estimated counting, authority weighting,
deduplication, conflict preservation, lost-in-the-middle placement, and overflow reduction.
"""

import pytest
from ai.context.models import (
    ContextBuildResult,
    ContextItem,
    CountingModeEnum,
    OverflowStatusEnum,
    PlacementEnum,
    SourceAuthorityEnum,
    TokenBudgetSpec,
)
from ai.context.token_budgeter import TokenBudgeter
from ai.context.context_manager import ContextManager
from ai.registry.models import ModelManifest
from ai.retrieval.reranker_provider import RerankResult


@pytest.fixture
def context_fixture():
    """Provides an isolated ContextManager and TokenBudgeter sandbox."""
    budgeter = TokenBudgeter(
        default_context_limit=2048,
        default_reserved_output=256,
        default_safety_reserve=64,
    )
    manager = ContextManager(budgeter=budgeter)
    return manager, budgeter


# ==============================================================================
# 1. TOKEN BUDGETING ARITHMETIC & COUNTING (1-5)
# ==============================================================================

def test_01_token_budget_calculation(context_fixture):
    """Test 1: Explicit token budget partitioning arithmetic."""
    _, budgeter = context_fixture

    manifest = ModelManifest(
        model_id="qwen2.5-3b-instruct",
        display_name="Qwen 3B",
        file_path="models/qwen.gguf",
        file_size_bytes=1000,
        sha256_checksum="a" * 64,
        context_length=4096,
        recommended_context_length=2048,
    )

    budget = budgeter.calculate_budget(
        model_manifest=manifest,
        system_prompt="System prompt test with several words",
        user_prompt="User query asking about plant opex electricity rates",
        reserved_output_tokens=512,
        safety_reserve_tokens=64,
    )

    assert budget.model_context_limit == 2048
    assert budget.reserved_output_tokens == 512
    assert budget.safety_reserve_tokens == 64
    assert budget.system_tokens > 0
    assert budget.user_tokens > 0
    # Equation: max_evidence = 2048 - (sys + usr + 512 + 64)
    expected_evidence = 2048 - (budget.system_tokens + budget.user_tokens + 512 + 64)
    assert budget.max_evidence_tokens == expected_evidence


def test_02_exact_vs_estimated_token_counting():
    """Test 2: Compares exact mock tokenizer vs estimated character fallback."""
    # 1. With exact tokenizer
    def mock_tokenizer(text: str) -> int:
        return len(text.split())

    exact_budgeter = TokenBudgeter(tokenizer_fn=mock_tokenizer)
    count_exact, mode_exact = exact_budgeter.count_tokens("Hello world from Hero Cost Intelligence")
    assert count_exact == 6
    assert mode_exact == CountingModeEnum.EXACT_TOKEN_COUNT

    # 2. Without tokenizer (estimated mode with 15% safety buffer)
    est_budgeter = TokenBudgeter()
    count_est, mode_est = est_budgeter.count_tokens("Hello world from Hero Cost Intelligence")
    assert count_est > 6
    assert mode_est == CountingModeEnum.ESTIMATED_TOKEN_COUNT


def test_03_override_context_limit(context_fixture):
    """Test 3: Override context limit takes precedence over manifest."""
    _, budgeter = context_fixture

    budget = budgeter.calculate_budget(
        override_context_limit=8192,
        reserved_output_tokens=1024,
        safety_reserve_tokens=128,
    )

    assert budget.model_context_limit == 8192
    assert budget.reserved_output_tokens == 1024
    assert budget.max_evidence_tokens > 6000


def test_04_zero_token_counts_on_empty_text(context_fixture):
    """Test 4: Empty string returns 0 tokens safely."""
    _, budgeter = context_fixture
    cnt, _ = budgeter.count_tokens("")
    assert cnt == 0
    cnt_ws, _ = budgeter.count_tokens("   \n\t ")
    assert cnt_ws == 0


def test_05_dynamic_recalculation_on_model_change(context_fixture):
    """Test 5: Recalculates budget when model context changes."""
    _, budgeter = context_fixture

    # Model A: 2048 context
    m_a = ModelManifest(
        model_id="model-2k",
        display_name="2k Model",
        file_path="m.gguf",
        file_size_bytes=10,
        sha256_checksum="b" * 64,
        recommended_context_length=2048,
    )
    b_a = budgeter.calculate_budget(model_manifest=m_a)

    # Model B: 8192 context
    m_b = ModelManifest(
        model_id="model-8k",
        display_name="8k Model",
        file_path="m.gguf",
        file_size_bytes=10,
        sha256_checksum="c" * 64,
        recommended_context_length=8192,
    )
    b_b = budgeter.calculate_budget(model_manifest=m_b)

    assert b_b.max_evidence_tokens > b_a.max_evidence_tokens


# ==============================================================================
# 2. AUTHORITY HIERARCHY & COMPOSITE PRIORITIZATION (6-10)
# ==============================================================================

def test_06_authority_weighting_hierarchy():
    """Test 6: Verifies standard authority class weight hierarchy."""
    assert SourceAuthorityEnum.AUTHORITATIVE_ENGINEERING.weight == 1.0
    assert SourceAuthorityEnum.BOM_MASTER_DATA.weight == 0.90
    assert SourceAuthorityEnum.PLANT_OPEX_ACTUALS.weight == 0.85
    assert SourceAuthorityEnum.HISTORICAL_IMPLEMENTATION.weight == 0.75
    assert SourceAuthorityEnum.IDEATHON_SUBMISSION.weight == 0.50
    assert SourceAuthorityEnum.SECONDARY_EXTERNAL.weight == 0.35


def test_07_composite_priority_calculation(context_fixture):
    """Test 7: Composite priority factors rerank score, authority weight, and exact ID."""
    manager, _ = context_fixture

    query = "Part 12345-ABC-001 mold amortisation"

    # High authority + ID match vs Low authority + no ID match
    p_high = manager._calculate_composite_priority(
        rerank_score=0.80,
        authority=SourceAuthorityEnum.AUTHORITATIVE_ENGINEERING,
        text="Part 12345-ABC-001 mold tooling cost breakdown",
        query=query,
    )

    p_low = manager._calculate_composite_priority(
        rerank_score=0.80,
        authority=SourceAuthorityEnum.IDEATHON_SUBMISSION,
        text="General mold tooling idea without specific part number",
        query=query,
    )

    assert p_high > p_low
    assert p_high == round((0.50 * 0.80) + (0.35 * 1.0) + (0.15 * 1.0), 4)


def test_08_evidence_deduplication_retains_highest_authority(context_fixture):
    """Test 8: Deduplication prunes near-duplicate in favor of higher-authority source."""
    manager, _ = context_fixture

    items = [
        ContextItem(
            source_id="IDEA-101",
            source_type="IDEATHON",
            authority_class=SourceAuthorityEnum.IDEATHON_SUBMISSION,
            text="Reduce paint shop primer oven temperature to 140C to save natural gas",
            token_count=20,
            rerank_score=0.75,
            composite_priority=0.60,
        ),
        ContextItem(
            source_id="ECN-2024-500",
            source_type="ECN",
            authority_class=SourceAuthorityEnum.AUTHORITATIVE_ENGINEERING,
            text="Reduce paint shop primer oven temperature to 140C to save natural gas consumption",
            token_count=22,
            rerank_score=0.80,
            composite_priority=0.85,
        ),
    ]

    kept, excluded, reasons = manager._deduplicate_evidence(items)

    assert len(kept) == 1
    assert kept[0].source_id == "ECN-2024-500"  # Authoritative ECN kept!
    assert len(excluded) == 1
    assert "IDEA-101" in reasons


def test_09_distinct_evidence_not_deduplicated(context_fixture):
    """Test 9: Technically distinct evidence is preserved without accidental pruning."""
    manager, _ = context_fixture

    items = [
        ContextItem(
            source_id="DOC-1",
            source_type="PLANT_OPEX",
            authority_class=SourceAuthorityEnum.PLANT_OPEX_ACTUALS,
            text="Neemrana plant electricity tariff rate per kWh is Rs 8.50",
            token_count=15,
            composite_priority=0.70,
        ),
        ContextItem(
            source_id="DOC-2",
            source_type="PLANT_OPEX",
            authority_class=SourceAuthorityEnum.PLANT_OPEX_ACTUALS,
            text="Haridwar plant electricity tariff rate per kWh is Rs 6.20",
            token_count=15,
            composite_priority=0.70,
        ),
    ]

    kept, excluded, _ = manager._deduplicate_evidence(items)
    assert len(kept) == 2
    assert len(excluded) == 0


def test_10_conflict_detection_and_flagging(context_fixture):
    """Test 10: Contradictory cost figures trigger conflict detection."""
    manager, _ = context_fixture

    items = [
        ContextItem(
            source_id="SOURCE-A",
            source_type="BOM",
            authority_class=SourceAuthorityEnum.BOM_MASTER_DATA,
            text="Splendor cylinder head casting unit cost is Rs 450.00",
            token_count=15,
        ),
        ContextItem(
            source_id="SOURCE-B",
            source_type="IDEATHON",
            authority_class=SourceAuthorityEnum.IDEATHON_SUBMISSION,
            text="Splendor cylinder head casting unit cost is Rs 380.00",
            token_count=15,
        ),
    ]

    has_conflict = manager._detect_conflicts(items)
    assert has_conflict is True
    assert items[0].is_conflicting is True
    assert items[1].is_conflicting is True


# ==============================================================================
# 3. LOST-IN-THE-MIDDLE PLACEMENT & OVERFLOW HANDLING (11-15)
# ==============================================================================

def test_11_lost_in_the_middle_placement(context_fixture):
    """Test 11: Places top authoritative items at BEGINNING and conflicting items at END."""
    manager, _ = context_fixture

    items = [
        ContextItem(source_id="C1", source_type="ECN", text="Top authority rule", token_count=10, composite_priority=0.95),
        ContextItem(source_id="C2", source_type="BOM", text="Background fact", token_count=10, composite_priority=0.60),
        ContextItem(source_id="C3", source_type="IDEA", text="Conflicting claim", token_count=10, composite_priority=0.50, is_conflicting=True),
    ]

    ordered = manager._assign_placements(items)

    assert ordered[0].source_id == "C1"
    assert ordered[0].placement == PlacementEnum.BEGINNING
    assert ordered[-1].source_id == "C3"
    assert ordered[-1].placement == PlacementEnum.END


def test_12_controlled_overflow_reduction(context_fixture):
    """Test 12: Prunes lower-priority items when evidence exceeds budget."""
    manager, _ = context_fixture

    # Budget max evidence = 50 tokens
    rerank_results = [
        RerankResult(
            id="DOC-HIGH",
            text="High priority authoritative engineering record text",
            initial_score=0.9,
            initial_rank=1,
            rerank_score=0.95,
            final_rank=1,
            matched_strategy="EXACT",
        ),
        RerankResult(
            id="DOC-MED",
            text="Medium priority BOM detail text",
            initial_score=0.6,
            initial_rank=2,
            rerank_score=0.65,
            final_rank=2,
            matched_strategy="TRIGRAM",
        ),
        RerankResult(
            id="DOC-LOW",
            text="Very long low priority ideathon suggestion that will exceed the remaining token budget comfortably. " * 10,
            initial_score=0.3,
            initial_rank=3,
            rerank_score=0.30,
            final_rank=3,
            matched_strategy="VECTOR",
        ),
    ]

    auth_map = {
        "DOC-HIGH": SourceAuthorityEnum.AUTHORITATIVE_ENGINEERING,
        "DOC-MED": SourceAuthorityEnum.BOM_MASTER_DATA,
        "DOC-LOW": SourceAuthorityEnum.IDEATHON_SUBMISSION,
    }

    res = manager.build_context(
        query="Engineering test query",
        reranked_results=rerank_results,
        authority_mapping=auth_map,
        override_context_limit=220,
        reserved_output_tokens=100,
        safety_reserve_tokens=20,
    )

    assert res.overflow_status == OverflowStatusEnum.OVERFLOW_REDUCED
    selected_ids = [item.source_id for item in res.selected_items]
    assert "DOC-HIGH" in selected_ids
    assert "DOC-LOW" in res.exclusion_reasons


def test_13_zero_candidate_build_context(context_fixture):
    """Test 13: 0 evidence produces clean prompt without crashing."""
    manager, _ = context_fixture

    res = manager.build_context(
        query="What is plant opex?",
        reranked_results=[],
    )

    assert res.overflow_status == OverflowStatusEnum.FIT
    assert len(res.selected_items) == 0
    assert "No evidence available." in res.assembled_prompt


def test_14_single_candidate_fastpath(context_fixture):
    """Test 14: Single evidence item placed at BEGINNING."""
    manager, _ = context_fixture

    cands = [
        RerankResult(
            id="DOC-SOLO",
            text="Single candidate evidence text",
            initial_score=0.8,
            initial_rank=1,
            rerank_score=0.85,
            final_rank=1,
            matched_strategy="EXACT",
        )
    ]

    res = manager.build_context(query="Query", reranked_results=cands)
    assert len(res.selected_items) == 1
    assert res.selected_items[0].placement == PlacementEnum.BEGINNING


def test_15_insufficient_context_budget_status(context_fixture):
    """Test 15: Flags INSUFFICIENT_CONTEXT when fixed overhead consumes entire budget."""
    manager, _ = context_fixture

    cands = [
        RerankResult(id="D1", text="Evidence", initial_score=0.8, initial_rank=1, rerank_score=0.8, final_rank=1, matched_strategy="EXACT")
    ]

    res = manager.build_context(
        query="Query",
        reranked_results=cands,
        override_context_limit=100,
        reserved_output_tokens=150,  # Exceeds limit
    )

    assert res.overflow_status == OverflowStatusEnum.INSUFFICIENT_CONTEXT
    assert len(res.selected_items) == 0


# ==============================================================================
# 4. DETERMINISM & PROVENANCE (16-20)
# ==============================================================================

def test_16_deterministic_assembly_reproducibility(context_fixture):
    """Test 16: Identical inputs produce byte-identical context outputs."""
    manager, _ = context_fixture

    cands = [
        RerankResult(id="D1", text="Sample A", initial_score=0.7, initial_rank=1, rerank_score=0.75, final_rank=1, matched_strategy="EXACT"),
        RerankResult(id="D2", text="Sample B", initial_score=0.6, initial_rank=2, rerank_score=0.65, final_rank=2, matched_strategy="VECTOR"),
    ]

    res1 = manager.build_context("Query", cands, request_id="fixed-uuid")
    res2 = manager.build_context("Query", cands, request_id="fixed-uuid")

    assert res1.assembled_prompt == res2.assembled_prompt
    assert res1.total_used_tokens == res2.total_used_tokens
    assert [i.source_id for i in res1.selected_items] == [i.source_id for i in res2.selected_items]


def test_17_full_provenance_recording(context_fixture):
    """Test 17: ContextBuildResult contains complete traceability metadata."""
    manager, _ = context_fixture

    res = manager.build_context(
        query="Query",
        reranked_results=[],
        request_id="REQ-777",
    )

    assert res.request_id == "REQ-777"
    assert "placement_strategy" in res.provenance
    assert "authority_weighting_version" in res.provenance
    assert res.context_version == "v1.0"


def test_18_system_and_user_prompts_preserved(context_fixture):
    """Test 18: System instructions and user prompt are cleanly formatted."""
    manager, _ = context_fixture

    res = manager.build_context(
        query="Calculate vehicle net saving",
        reranked_results=[],
        system_prompt="Custom System Rule 123",
    )

    assert "<SYSTEM_INSTRUCTION>\nCustom System Rule 123\n</SYSTEM_INSTRUCTION>" in res.assembled_prompt
    assert "<USER_QUERY>\nCalculate vehicle net saving\n</USER_QUERY>" in res.assembled_prompt


def test_19_critical_constraints_placed_at_end(context_fixture):
    """Test 19: Mandatory constraints placed at END for maximum attention."""
    manager, _ = context_fixture

    items = [
        ContextItem(source_id="A", source_type="BOM", text="General BOM info", token_count=10, composite_priority=0.8),
        ContextItem(source_id="B", source_type="POLICY", text="Mandatory constraint: Never double count electricity", token_count=10, composite_priority=0.7),
    ]

    ordered = manager._assign_placements(items)
    assert ordered[-1].source_id == "B"
    assert ordered[-1].placement == PlacementEnum.END


def test_20_evidence_tokens_and_remaining_calculation(context_fixture):
    """Test 20: Accurately reports evidence tokens and remaining available capacity."""
    manager, _ = context_fixture

    cands = [
        RerankResult(id="D1", text="Ten word sample evidence sentence for token count testing", initial_score=0.8, initial_rank=1, rerank_score=0.8, final_rank=1, matched_strategy="EXACT")
    ]

    res = manager.build_context(query="Query", reranked_results=cands, override_context_limit=1000)

    assert res.evidence_tokens > 0
    assert res.total_used_tokens == res.system_tokens + res.user_tokens + res.evidence_tokens + res.reserved_output_tokens + res.safety_reserve_tokens
    assert res.remaining_available_tokens == 1000 - res.total_used_tokens
