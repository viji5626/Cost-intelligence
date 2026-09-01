"""
Vehicle Ideathon Engineering Taxonomy & Synonym Dictionaries
Provides domain-specific vehicle aliases, component synonyms, and cost-reduction category keyword maps.
"""

import re
from typing import Dict, List, Pattern, Tuple
from database.models.ideathon import CostReductionCategory

# Hero Vehicle Model Synonyms and Alias Dictionary
VEHICLE_MODEL_ALIASES: Dict[str, List[str]] = {
    "SPLENDOR_PLUS": [
        "splendor+", "splendor plus", "splendor", "splendor +", "splendor xtec", "splendor ismart", "apdv splendor"
    ],
    "HF_DELUXE": [
        "hf deluxe", "hf-deluxe", "hf deluxe eco", "hf 100", "hf-100", "deluxe"
    ],
    "GLAMOUR": [
        "glamour", "glamour xtec", "glamour 125", "glamour sv"
    ],
    "PASSION_PLUS": [
        "passion", "passion+", "passion plus", "passion pro", "passion xtec"
    ],
    "XPULSE_200": [
        "xpulse", "xpulse 200", "xpulse 200 4v", "xpulse 200t", "rally edition"
    ],
    "XTREME_160R": [
        "xtreme", "xtreme 160r", "xtreme 160r 4v", "xtreme 200s", "xtreme 125r"
    ],
    "VIDA_V1": [
        "vida", "vida v1", "vida v1 pro", "vida v1 plus", "vida ev"
    ],
    "ZOOM_110": [
        "xoom", "xoom 110", "zoom", "zoom 110", "xoom zx"
    ],
}

# Subsystem and Component Synonym Mappings
COMPONENT_SYNONYMS: Dict[str, List[str]] = {
    "CYLINDER_HEAD_COVER": [
        "cylinder head cover", "head cover", "valve cover", "rocker cover", "tappet cover"
    ],
    "PISTON_PIN": [
        "piston pin", "gudgeon pin", "wrist pin", "pin piston"
    ],
    "HANDLEBAR_WEIGHT": [
        "handlebar weight", "handle balancer", "bar end weight", "handle bar end", "handle weight"
    ],
    "MAIN_STAND": [
        "main stand", "center stand", "centre stand", "stand comp main"
    ],
    "SIDE_STAND": [
        "side stand", "prop stand", "stand comp side"
    ],
    "FRONT_FENDER": [
        "front fender", "front mudguard", "fender comp fr", "front mud guard"
    ],
    "CHAIN_COVER": [
        "chain cover", "chain case", "drive chain case", "gear case"
    ],
    "FASTENER_M6": [
        "m6 bolt", "m6 screw", "flange bolt 6x12", "bolt flange 6mm", "m6 hex"
    ],
}

# Part Number Regex Patterns for Automotive Standard Formats
# E.g., 11100-KCC-900, 53100-KTR-900, 12100-AA1-000, 90111-187-000
PART_NUMBER_REGEX: Pattern = re.compile(r"\b([0-9]{5}-[A-Z0-9]{3}-[A-Z0-9]{3,4})\b", re.IGNORECASE)

# Category Keyword Matching Dictionary
CATEGORY_KEYWORD_RULES: List[Tuple[CostReductionCategory, List[str]]] = [
    (
        CostReductionCategory.MATERIAL_SUBSTITUTION,
        ["material change", "substitute", "aluminum to plastic", "steel to polymer", "nylon", "polypropylene", "grade change", "raw material change"]
    ),
    (
        CostReductionCategory.GEOMETRY_OPTIMIZATION,
        ["thickness reduction", "wall thickness", "rib optimization", "weight reduction", "weight saving", "geometry", "dimension reduction", "downsizing"]
    ),
    (
        CostReductionCategory.FASTENER_CONSOLIDATION,
        ["fastener", "bolt reduction", "screw elimination", "snap fit", "clip", "m6", "m8", "nut elimination", "hardware consolidation"]
    ),
    (
        CostReductionCategory.PROCESS_SIMPLIFICATION,
        ["machining elimination", "cycle time", "single shot molding", "powder coating to paint", "die cast", "eliminate heat treatment", "process step"]
    ),
    (
        CostReductionCategory.LOCAL_SOURCING,
        ["local vendor", "indigenization", "import substitution", "local source", "domestic supplier", "freight saving"]
    ),
    (
        CostReductionCategory.PACKAGING_LOGISTICS,
        ["packaging", "returnable bin", "nesting", "pallet density", "box size", "corrugated box", "freight optimization"]
    ),
    (
        CostReductionCategory.FEATURE_RATIONALIZATION,
        ["eliminate bracket", "remove sticker", "redundant bracket", "feature rationalization", "part elimination", "decontenting"]
    ),
]

# Automotive Safety-Critical Components Classification (Steering, Braking, Chassis, Suspension)
SAFETY_CRITICAL_COMPONENTS: List[str] = [
    "handlebar", "steering handle", "brake lever", "brake disc", "brake drum", "brake pedal",
    "master cylinder", "caliper", "front fork", "rear swingarm", "chassis frame", "main frame",
    "front axle", "rear axle", "wheel rim", "tire", "fuel tank", "throttle body"
]
