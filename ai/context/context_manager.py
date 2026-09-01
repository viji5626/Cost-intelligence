"""
Context Manager Module
Implements evidence deduplication, authority-driven composite prioritization,
conflict preservation, lost-in-the-middle controlled placement, and overflow budgeting.
"""

import re
import uuid
from typing import Any, Dict, List, Optional, Set, Tuple
from ai.context.models import (
    ContextBuildResult,
    ContextItem,
    CountingModeEnum,
    OverflowStatusEnum,
    PlacementEnum,
    SourceAuthorityEnum,
    TokenBudgetSpec,
)
from ai.context.token_budgeter import TokenBudgeter, token_budgeter
from ai.registry.models import ModelManifest
from ai.retrieval.reranker_provider import RerankResult


class ContextManager:
    """
    Deterministic Context Orchestrator.
    Constructs high-relevance, authority-weighted, and token-bounded context payloads for generative SLMs.
    """

    def __init__(
        self,
        budgeter: Optional[TokenBudgeter] = None,
        duplicate_similarity_threshold: float = 0.88,
    ):
        self.budgeter = budgeter or token_budgeter
        self.duplicate_similarity_threshold = duplicate_similarity_threshold

    def _calculate_jaccard_similarity(self, text_a: str, text_b: str) -> float:
        """Calculates token Jaccard similarity between two texts."""
        tokens_a = set(re.findall(r"[a-z0-9\-_]+", text_a.lower()))
        tokens_b = set(re.findall(r"[a-z0-9\-_]+", text_b.lower()))
        if not tokens_a or not tokens_b:
            return 0.0
        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        return len(intersection) / len(union)

    def _detect_conflicts(self, items: List[ContextItem]) -> bool:
        """
        Detects if items contain conflicting engineering or cost figures.
        Marks conflicting items and returns True if conflicts exist.
        """
        has_conflict = False
        # Compare numerical claims associated with the same target keywords
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                item_a = items[i]
                item_b = items[j]

                # Check if discussing the same part/plant with different cost numbers
                nums_a = set(re.findall(r"\b\d+(?:\.\d+)?\b", item_a.text))
                nums_b = set(re.findall(r"\b\d+(?:\.\d+)?\b", item_b.text))

                # If overlapping tokens > 0.4 but differing numbers
                sim = self._calculate_jaccard_similarity(item_a.text, item_b.text)
                if 0.35 <= sim < 0.85 and nums_a != nums_b and len(nums_a) > 0 and len(nums_b) > 0:
                    item_a.is_conflicting = True
                    item_b.is_conflicting = True
                    has_conflict = True

        return has_conflict

    def _deduplicate_evidence(
        self,
        raw_items: List[ContextItem],
    ) -> Tuple[List[ContextItem], List[Dict[str, Any]], Dict[str, str]]:
        """
        Deduplicates near-identical evidence chunks, retaining the highest-authority source.
        """
        kept: List[ContextItem] = []
        excluded: List[Dict[str, Any]] = []
        reasons: Dict[str, str] = {}

        # Sort candidate pool by authority weight (descending), then composite priority
        sorted_candidates = sorted(
            raw_items,
            key=lambda x: (x.authority_class.weight, x.composite_priority),
            reverse=True,
        )

        for cand in sorted_candidates:
            is_duplicate = False
            for existing in kept:
                sim = self._calculate_jaccard_similarity(cand.text, existing.text)
                if sim >= self.duplicate_similarity_threshold:
                    is_duplicate = True
                    excluded.append(cand.model_dump())
                    reasons[cand.source_id] = (
                        f"Duplicate evidence pruned in favor of higher-authority source '{existing.source_id}' "
                        f"(Similarity: {sim:.2f}, Auth: {existing.authority_class.value})"
                    )
                    break

            if not is_duplicate:
                kept.append(cand)

        return kept, excluded, reasons

    def _calculate_composite_priority(
        self,
        rerank_score: float,
        authority: SourceAuthorityEnum,
        text: str,
        query: str,
    ) -> float:
        """
        Calculates holistic composite priority:
        Composite = 0.50 * Rerank_Score + 0.35 * Authority_Weight + 0.15 * Exact_ID_Match
        """
        # Exact ID match check
        part_matches = re.findall(r"\b\d{5}-[a-z0-9]{3,5}-\w{3,5}\b", query.lower())
        ecn_matches = re.findall(r"\bec[nr]-\d{4}-\d{3,5}\b", query.lower())
        target_ids = set(part_matches + ecn_matches)

        has_id_match = any(tid in text.lower() for tid in target_ids)
        id_score = 1.0 if has_id_match else 0.0

        composite = (0.50 * rerank_score) + (0.35 * authority.weight) + (0.15 * id_score)
        return round(composite, 4)

    def _assign_placements(self, items: List[ContextItem]) -> List[ContextItem]:
        """
        Applies Lost-In-The-Middle mitigation strategy.
        - BEGINNING: Top authoritative & primary evidence
        - MIDDLE: Supporting context & background facts
        - END: Conflicting evidence, critical constraints, concluding rules closest to user query
        """
        if not items:
            return []

        if len(items) == 1:
            items[0].placement = PlacementEnum.BEGINNING
            return items

        # Sort descending by composite priority
        ranked = sorted(items, key=lambda x: x.composite_priority, reverse=True)

        beginning_items: List[ContextItem] = []
        middle_items: List[ContextItem] = []
        end_items: List[ContextItem] = []

        for idx, item in enumerate(ranked):
            # Critical / conflicting items placed at the END (closest to query attention)
            if item.is_conflicting or "constraint" in item.text.lower() or "mandatory" in item.text.lower():
                item.placement = PlacementEnum.END
                end_items.append(item)
            elif idx < max(1, len(ranked) // 3):
                item.placement = PlacementEnum.BEGINNING
                beginning_items.append(item)
            else:
                item.placement = PlacementEnum.MIDDLE
                middle_items.append(item)

        # Assemble final ordered sequence: BEGINNING -> MIDDLE -> END
        return beginning_items + middle_items + end_items

    def build_context(
        self,
        query: str,
        reranked_results: List[RerankResult],
        system_prompt: str = "You are the Hero Cost Intelligence AI. Answer accurately using only verified engineering evidence.",
        model_manifest: Optional[ModelManifest] = None,
        authority_mapping: Optional[Dict[str, SourceAuthorityEnum]] = None,
        override_context_limit: Optional[int] = None,
        reserved_output_tokens: Optional[int] = None,
        safety_reserve_tokens: Optional[int] = None,
        request_id: Optional[str] = None,
    ) -> ContextBuildResult:
        """
        Orchestrates deterministic context construction, token budgeting, deduplication, and placement.
        """
        req_id = request_id or str(uuid.uuid4())
        auth_map = authority_mapping or {}

        # 1. Calculate dynamic token budget
        budget = self.budgeter.calculate_budget(
            model_manifest=model_manifest,
            system_prompt=system_prompt,
            user_prompt=query,
            override_context_limit=override_context_limit,
            reserved_output_tokens=reserved_output_tokens,
            safety_reserve_tokens=safety_reserve_tokens,
        )

        # 2. Transform RerankResults to ContextItems
        raw_items: List[ContextItem] = []
        for r in reranked_results:
            auth_class = auth_map.get(r.id, SourceAuthorityEnum.SECONDARY_EXTERNAL)
            tokens, count_mode = self.budgeter.count_tokens(r.text)
            comp_prio = self._calculate_composite_priority(
                rerank_score=r.rerank_score,
                authority=auth_class,
                text=r.text,
                query=query,
            )
            raw_items.append(
                ContextItem(
                    source_id=r.id,
                    source_type=str(r.metadata.get("entity_type", "UNKNOWN") if r.metadata else "UNKNOWN"),
                    authority_class=auth_class,
                    text=r.text,
                    token_count=tokens,
                    counting_mode=count_mode,
                    original_rank=r.initial_rank,
                    rerank_score=r.rerank_score,
                    composite_priority=comp_prio,
                    metadata=r.metadata or {},
                )
            )

        # 3. Deduplicate
        deduped_items, excluded_items, exclusion_reasons = self._deduplicate_evidence(raw_items)

        # 4. Conflict Detection
        has_conflicts = self._detect_conflicts(deduped_items)

        # 5. Token Budget Allocation & Controlled Overflow Reduction
        selected_items: List[ContextItem] = []
        current_evidence_tokens = 0
        overflow_status = OverflowStatusEnum.FIT

        # Sort remaining by composite priority
        prio_sorted = sorted(deduped_items, key=lambda x: x.composite_priority, reverse=True)

        for item in prio_sorted:
            if current_evidence_tokens + item.token_count <= budget.max_evidence_tokens:
                selected_items.append(item)
                current_evidence_tokens += item.token_count
            else:
                overflow_status = OverflowStatusEnum.OVERFLOW_REDUCED
                excluded_items.append(item.model_dump())
                exclusion_reasons[item.source_id] = (
                    f"Excluded due to token budget constraint ({item.token_count} tokens exceed remaining "
                    f"budget of {budget.max_evidence_tokens - current_evidence_tokens} tokens)"
                )

        if not selected_items and deduped_items and budget.max_evidence_tokens <= 0:
            overflow_status = OverflowStatusEnum.INSUFFICIENT_CONTEXT

        # 6. Apply Lost-In-The-Middle Placement Strategy
        final_ordered_items = self._assign_placements(selected_items)

        # 7. Assemble Formatted Context Prompt
        context_blocks = []
        for item in final_ordered_items:
            tag = f"[EVIDENCE #{item.source_id} | AUTH: {item.authority_class.value} | PRIO: {item.composite_priority:.2f}]"
            context_blocks.append(f"{tag}\n{item.text}")

        evidence_section = "\n\n".join(context_blocks) if context_blocks else "No evidence available."
        assembled_prompt = (
            f"<SYSTEM_INSTRUCTION>\n{system_prompt}\n</SYSTEM_INSTRUCTION>\n\n"
            f"<VERIFIED_EVIDENCE>\n{evidence_section}\n</VERIFIED_EVIDENCE>\n\n"
            f"<USER_QUERY>\n{query}\n</USER_QUERY>"
        )

        total_used = (
            budget.system_tokens
            + budget.user_tokens
            + current_evidence_tokens
            + budget.reserved_output_tokens
            + budget.safety_reserve_tokens
        )
        remaining = max(0, budget.model_context_limit - total_used)

        model_id = model_manifest.model_id if model_manifest else "default-model"

        return ContextBuildResult(
            request_id=req_id,
            model_id=model_id,
            model_context_limit=budget.model_context_limit,
            counting_mode=budget.counting_mode,
            system_tokens=budget.system_tokens,
            user_tokens=budget.user_tokens,
            evidence_tokens=current_evidence_tokens,
            reserved_output_tokens=budget.reserved_output_tokens,
            safety_reserve_tokens=budget.safety_reserve_tokens,
            total_used_tokens=total_used,
            remaining_available_tokens=remaining,
            selected_items=final_ordered_items,
            excluded_items=excluded_items,
            exclusion_reasons=exclusion_reasons,
            assembled_prompt=assembled_prompt,
            overflow_status=overflow_status,
            has_conflicting_evidence=has_conflicts,
            context_version="v1.0",
            provenance={
                "request_id": req_id,
                "model_id": model_id,
                "placement_strategy": "LOST_IN_THE_MIDDLE_3_TIER",
                "authority_weighting_version": "v1.0",
            },
        )


# Global singleton
context_manager = ContextManager()
