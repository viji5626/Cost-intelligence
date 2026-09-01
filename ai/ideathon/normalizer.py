"""
Ideathon Normalization & Entity Extraction Engine
Performs deterministic text decomposition, vehicle model extraction, component/part mapping,
BOM classification, data quality scoring, and duplicate similarity computation.
"""

import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple
from ai.ideathon.taxonomy import (
    CATEGORY_KEYWORD_RULES,
    COMPONENT_SYNONYMS,
    PART_NUMBER_REGEX,
    VEHICLE_MODEL_ALIASES,
)
from database.models.ideathon import (
    CostReductionCategory,
    DataQualityStatus,
    IdeaDecisionState,
    ImplementationEvidenceState,
)


class NormalizedIdeaResult:
    """Encapsulates normalized extraction outputs for an Ideathon idea."""

    def __init__(
        self,
        raw_title: str,
        raw_description: str,
        decomposed_problem: str,
        decomposed_solution: str,
        decomposed_expected_benefit: str,
        extracted_vehicle_alias: Optional[str],
        extracted_component_alias: Optional[str],
        extracted_part_number: Optional[str],
        extracted_synonyms: List[str],
        is_bom_linked: bool,
        cost_reduction_category: CostReductionCategory,
        data_quality: DataQualityStatus,
        extraction_confidence: float,
        part_match_confidence: float,
        claimed_saving_per_veh: Optional[Decimal] = None,
    ):
        self.raw_title = raw_title
        self.raw_description = raw_description
        self.decomposed_problem = decomposed_problem
        self.decomposed_solution = decomposed_solution
        self.decomposed_expected_benefit = decomposed_expected_benefit
        self.extracted_vehicle_alias = extracted_vehicle_alias
        self.extracted_component_alias = extracted_component_alias
        self.extracted_part_number = extracted_part_number
        self.extracted_synonyms = extracted_synonyms
        self.is_bom_linked = is_bom_linked
        self.cost_reduction_category = cost_reduction_category
        self.data_quality = data_quality
        self.extraction_confidence = extraction_confidence
        self.part_match_confidence = part_match_confidence
        self.claimed_saving_per_veh = claimed_saving_per_veh


class IdeaNormalizer:
    """Normalizes raw idea text into structured engineering entities."""

    @classmethod
    def decompose_text(cls, title: str, description: str) -> Tuple[str, str, str]:
        """
        Decomposes unstructured description into Problem, Proposed Solution, and Expected Benefit.
        Uses structured delimiters if present, or heuristic sentence partitioning.
        """
        full_text = f"{title}\n{description}".strip()
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]

        problem_parts: List[str] = []
        solution_parts: List[str] = []
        benefit_parts: List[str] = []

        current_section = "PROBLEM"

        for line in lines:
            lower = line.lower()
            if any(k in lower for k in ["problem:", "issue:", "existing situation:", "current design:", "pain point:"]):
                current_section = "PROBLEM"
                problem_parts.append(re.sub(r"^(problem|issue|existing situation|current design|pain point):", "", line, flags=re.IGNORECASE).strip())
            elif any(k in lower for k in ["solution:", "proposed change:", "proposal:", "recommendation:", "idea:"]):
                current_section = "SOLUTION"
                solution_parts.append(re.sub(r"^(solution|proposed change|proposal|recommendation|idea):", "", line, flags=re.IGNORECASE).strip())
            elif any(k in lower for k in ["saving:", "benefit:", "expected saving:", "cost impact:", "advantage:"]):
                current_section = "BENEFIT"
                benefit_parts.append(re.sub(r"^(saving|benefit|expected saving|cost impact|advantage):", "", line, flags=re.IGNORECASE).strip())
            else:
                if current_section == "PROBLEM":
                    problem_parts.append(line)
                elif current_section == "SOLUTION":
                    solution_parts.append(line)
                elif current_section == "BENEFIT":
                    benefit_parts.append(line)

        # Fallback if no sections were explicitly demarcated
        if not solution_parts and len(lines) >= 2:
            problem = lines[0]
            solution = " ".join(lines[1:])
            benefit = "Cost reduction per vehicle"
        else:
            problem = " ".join(problem_parts) if problem_parts else title
            solution = " ".join(solution_parts) if solution_parts else description
            benefit = " ".join(benefit_parts) if benefit_parts else "Cost reduction per vehicle"

        return problem, solution, benefit

    @classmethod
    def extract_vehicle_model(cls, text: str) -> Tuple[Optional[str], float]:
        """Extracts canonical vehicle model code from text using synonym dictionary."""
        lower = text.lower()
        matched_models: List[str] = []

        for model_key, aliases in VEHICLE_MODEL_ALIASES.items():
            for alias in aliases:
                # Use word boundary search
                pattern = r"\b" + re.escape(alias) + r"\b"
                if re.search(pattern, lower):
                    matched_models.append(model_key)
                    break

        if len(matched_models) == 1:
            return matched_models[0], 0.95
        elif len(matched_models) > 1:
            # Ambiguous: mentions multiple vehicles (e.g. "Applicable to Splendor and HF Deluxe")
            return matched_models[0], 0.70  # Primary match with lower confidence
        return None, 0.0

    @classmethod
    def extract_part_number_and_component(cls, text: str) -> Tuple[Optional[str], Optional[str], List[str], float]:
        """Extracts part drawing number and component synonym from text."""
        # 1. Regex part number search
        match = PART_NUMBER_REGEX.search(text)
        part_no = match.group(1).upper() if match else None

        # 2. Component synonym search
        lower = text.lower()
        matched_component: Optional[str] = None
        synonyms_found: List[str] = []

        for comp_key, syn_list in COMPONENT_SYNONYMS.items():
            for syn in syn_list:
                if syn in lower:
                    matched_component = comp_key
                    synonyms_found.append(syn)
                    break

        if part_no and matched_component:
            return part_no, matched_component, synonyms_found, 0.98
        elif part_no:
            return part_no, None, [part_no], 0.90
        elif matched_component:
            return None, matched_component, synonyms_found, 0.80
        return None, None, [], 0.0

    @classmethod
    def classify_category(cls, text: str) -> CostReductionCategory:
        """Classifies the idea into one of the standard CostReductionCategory values."""
        lower = text.lower()
        for category, keywords in CATEGORY_KEYWORD_RULES:
            for kw in keywords:
                if kw in lower:
                    return category
        return CostReductionCategory.OTHER_VAVE

    @classmethod
    def normalize_submission(
        cls,
        title: str,
        description: str,
        raw_claimed_saving: Optional[Any] = None,
    ) -> NormalizedIdeaResult:
        """Main entry point for decomposing and normalizing a raw idea submission."""
        full_text = f"{title}\n{description}".strip()

        # 1. Decompose text
        problem, solution, benefit = cls.decompose_text(title, description)

        # 2. Entity extraction
        veh_model, veh_conf = cls.extract_vehicle_model(full_text)
        part_no, comp_alias, syns, part_conf = cls.extract_part_number_and_component(full_text)

        # 3. Category classification
        category = cls.classify_category(full_text)

        # 4. BOM linkage classification
        is_bom = category not in [CostReductionCategory.PACKAGING_LOGISTICS, CostReductionCategory.LOCAL_SOURCING]

        # 5. Extraction confidence & Data Quality assessment
        if not title.strip() or len(description.strip()) < 10:
            data_quality = DataQualityStatus.MISSING_DATA
            overall_conf = 0.20
        elif not veh_model and not comp_alias and not part_no:
            data_quality = DataQualityStatus.REQUIRES_HUMAN_REVIEW
            overall_conf = 0.40
        elif not veh_model:
            data_quality = DataQualityStatus.AMBIGUOUS_VEHICLE
            overall_conf = 0.60
        elif not comp_alias and not part_no:
            data_quality = DataQualityStatus.AMBIGUOUS_COMPONENT
            overall_conf = 0.60
        else:
            data_quality = DataQualityStatus.COMPLETE
            overall_conf = round((veh_conf + (part_conf or 0.8)) / 2.0, 2)

        # Parse claimed saving if present
        claimed_dec: Optional[Decimal] = None
        if raw_claimed_saving is not None:
            try:
                claimed_dec = Decimal(str(raw_claimed_saving))
            except Exception:
                pass

        return NormalizedIdeaResult(
            raw_title=title.strip(),
            raw_description=description.strip(),
            decomposed_problem=problem,
            decomposed_solution=solution,
            decomposed_expected_benefit=benefit,
            extracted_vehicle_alias=veh_model,
            extracted_component_alias=comp_alias,
            extracted_part_number=part_no,
            extracted_synonyms=syns,
            is_bom_linked=is_bom,
            cost_reduction_category=category,
            data_quality=data_quality,
            extraction_confidence=overall_conf,
            part_match_confidence=part_conf,
            claimed_saving_per_veh=claimed_dec,
        )

    @classmethod
    def calculate_idea_similarity(cls, title_a: str, desc_a: str, title_b: str, desc_b: str) -> float:
        """
        Computes lexical/token Jaccard, stem prefix, and title similarity between two ideas.
        Returns similarity score (0.0 to 1.0).
        """
        def _tokenize(s: str) -> Set[str]:
            words = re.findall(r"[a-z0-9]+", s.lower())
            stopwords = {"the", "a", "an", "in", "on", "of", "to", "for", "is", "and", "by", "with", "from", "reduce", "optimization"}
            # Use 4-char prefix stem for fuzzy word matching (e.g. weight, weights, weighting -> weig)
            return {w[:4] if len(w) >= 4 else w for w in words if len(w) >= 3 and w not in stopwords}

        tokens_a = _tokenize(f"{title_a} {desc_a}")
        tokens_b = _tokenize(f"{title_b} {desc_b}")

        if not tokens_a or not tokens_b:
            return 0.0

        intersection = len(tokens_a.intersection(tokens_b))
        union = len(tokens_a.union(tokens_b))
        jaccard = intersection / union if union > 0 else 0.0

        title_a_clean = title_a.lower().strip()
        title_b_clean = title_b.lower().strip()
        if title_a_clean == title_b_clean:
            return 1.0

        return round(jaccard, 4)
