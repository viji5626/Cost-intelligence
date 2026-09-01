"""
AI Grammar Subsystem (AI-10)
Exports GBNF compiler, domain schemas, and StructuredOutputEngine.
"""

from ai.grammar.gbnf_compiler import (
    GBNFCapabilityEnum,
    GBNFCompiler,
    UnsupportedGrammarSchemaError,
)
from ai.grammar.schemas import (
    EvidenceSynthesisOutputSchema,
    IdeaDecompositionOutputSchema,
    OpexBenchmarkingHypothesisSchema,
    OpportunitySimulationOutputSchema,
    ToolCallOutputSchema,
)
from ai.grammar.structured_engine import (
    StructuredGenerationResult,
    StructuredOutputEngine,
    StructuredResultProvenance,
)

__all__ = [
    "GBNFCapabilityEnum",
    "GBNFCompiler",
    "UnsupportedGrammarSchemaError",
    "IdeaDecompositionOutputSchema",
    "EvidenceSynthesisOutputSchema",
    "OpportunitySimulationOutputSchema",
    "OpexBenchmarkingHypothesisSchema",
    "ToolCallOutputSchema",
    "StructuredGenerationResult",
    "StructuredOutputEngine",
    "StructuredResultProvenance",
]
