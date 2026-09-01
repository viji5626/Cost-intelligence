"""
Bounded Query Formulation & Multi-Faceted Engineering Search Strategy
Integrates canonical taxonomy and normalization from ai.ideathon.taxonomy and ai.ideathon.normalizer.
Enforces single source of truth for engineering entities and avoids unbounded expansions.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from ai.ideathon.normalizer import IdeaNormalizer
from ai.ideathon.taxonomy import (
    CATEGORY_KEYWORD_RULES,
    COMPONENT_SYNONYMS,
    PART_NUMBER_REGEX,
    VEHICLE_MODEL_ALIASES,
)


@dataclass
class FormulatedQuery:
    """Encapsulates a formulated multi-channel engineering query with resolved facets."""
    raw_query: str
    primary_search_text: str
    target_part_number: Optional[str] = None
    target_ecn_code: Optional[str] = None
    target_vehicle_model: Optional[str] = None
    target_component: Optional[str] = None
    target_category: Optional[str] = None
    decomposed_problem: Optional[str] = None
    decomposed_solution: Optional[str] = None
    expanded_terms: List[str] = field(default_factory=list)
    extraction_confidence: float = 1.0


class QueryFormulator:
    """
    Formulates structured retrieval queries from ideas or engineering tasks.
    Delegates canonical entity resolution exclusively to the project's Ideathon taxonomy.
    """

    PART_NUMBER_REGEX = re.compile(r"\b([0-9]{5}-[A-Z0-9]{3,4}-[A-Z0-9]{3,4})\b", re.IGNORECASE)
    ECN_REGEX = re.compile(r"\b(?:ECN|ECR)-\d{4}-\d{3,5}\b", re.IGNORECASE)

    @classmethod
    def extract_exact_identifiers(cls, text: str) -> Dict[str, Optional[str]]:
        """Extracts exact Part Numbers, ECN/ECR codes, and canonical Vehicle Models."""
        part_match = cls.PART_NUMBER_REGEX.search(text)
        ecn_match = cls.ECN_REGEX.search(text)

        # Canonical vehicle model resolution using VEHICLE_MODEL_ALIASES
        matched_model: Optional[str] = None
        text_lower = text.lower()
        for canonical_model, aliases in VEHICLE_MODEL_ALIASES.items():
            for alias in aliases:
                pattern = r"\b" + re.escape(alias) + r"\b"
                if re.search(pattern, text_lower):
                    matched_model = canonical_model
                    break
            if matched_model:
                break

        # Canonical component resolution using COMPONENT_SYNONYMS
        matched_component: Optional[str] = None
        for canonical_comp, synonyms in COMPONENT_SYNONYMS.items():
            for syn in synonyms:
                pattern = r"\b" + re.escape(syn) + r"\b"
                if re.search(pattern, text_lower):
                    matched_component = canonical_comp
                    break
            if matched_component:
                break

        return {
            "part_number": part_match.group(0).upper() if part_match else None,
            "ecn_code": ecn_match.group(0).upper() if ecn_match else None,
            "model_code": matched_model,
            "component_code": matched_component,
        }

    @classmethod
    def formulate_query(
        cls,
        raw_text: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        target_part_number: Optional[str] = None,
        target_vehicle_model: Optional[str] = None,
    ) -> FormulatedQuery:
        """
        Formulates search facets and bounded query expansions.
        Reuses IdeaNormalizer for text decomposition and taxonomy lookup.
        """
        full_text = f"{title or ''} {description or ''} {raw_text}".strip()

        # 1. Exact Identifier Extraction
        ids = cls.extract_exact_identifiers(full_text)
        part_no = target_part_number or ids["part_number"]
        ecn_no = ids["ecn_code"]
        model_code = target_vehicle_model or ids["model_code"]
        comp_code = ids["component_code"]

        # 2. Text Decomposition via IdeaNormalizer
        problem = ""
        solution = ""
        category_name: Optional[str] = None

        if title or description:
            try:
                norm_res = IdeaNormalizer.normalize_submission(
                    title=title or raw_text,
                    description=description or raw_text,
                )
                problem = norm_res.decomposed_problem
                solution = norm_res.decomposed_solution
                category_name = norm_res.cost_reduction_category.value if norm_res.cost_reduction_category else None
                if not part_no and norm_res.extracted_part_number:
                    part_no = norm_res.extracted_part_number
                if not model_code and norm_res.extracted_vehicle_alias:
                    model_code = norm_res.extracted_vehicle_alias
                if not comp_code and norm_res.extracted_component_alias:
                    comp_code = norm_res.extracted_component_alias
            except Exception:
                pass

        # 3. Bounded, Deterministic Query Expansion via Canonical Taxonomy
        expanded_terms_set: Set[str] = set()

        if comp_code and comp_code in COMPONENT_SYNONYMS:
            for syn in COMPONENT_SYNONYMS[comp_code]:
                expanded_terms_set.add(syn)

        if model_code and model_code in VEHICLE_MODEL_ALIASES:
            for alias in VEHICLE_MODEL_ALIASES[model_code][:3]:
                expanded_terms_set.add(alias)

        # Primary search text construction
        components = []
        if part_no:
            components.append(part_no)
        if ecn_no:
            components.append(ecn_no)
        if model_code:
            components.append(model_code.replace("_", " "))
        if comp_code:
            components.append(comp_code.replace("_", " "))
        if solution:
            components.append(solution)
        elif raw_text:
            components.append(raw_text)

        primary_text = " ".join(components) if components else raw_text

        return FormulatedQuery(
            raw_query=raw_text,
            primary_search_text=primary_text,
            target_part_number=part_no,
            target_ecn_code=ecn_no,
            target_vehicle_model=model_code,
            target_component=comp_code,
            target_category=category_name,
            decomposed_problem=problem or None,
            decomposed_solution=solution or None,
            expanded_terms=sorted(list(expanded_terms_set)),
            extraction_confidence=0.95 if (part_no or ecn_no) else 0.80,
        )
