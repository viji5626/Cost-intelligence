"""
Phase AI-10 Test Suite: Structured Output & GBNF Grammar Engine
Tests GBNF compiler capabilities, domain schemas, dual-path execution,
Pydantic semantic validation, auto-repair retry loops, failure modes, and provenance integrity.
"""

import asyncio
import json
import os
import shutil
import tempfile
from enum import Enum
from typing import List, Literal, Optional
import pytest
from pydantic import BaseModel, Field, ValidationError

from ai.core.contracts import TaskType
from ai.grammar.gbnf_compiler import GBNFCapabilityEnum, GBNFCompiler, UnsupportedGrammarSchemaError
from ai.grammar.schemas import (
    EvidenceSynthesisOutputSchema,
    IdeaDecompositionOutputSchema,
    OpexBenchmarkingHypothesisSchema,
    OpportunitySimulationOutputSchema,
    ToolCallOutputSchema,
)
from ai.grammar.structured_engine import StructuredOutputEngine, StructuredResultProvenance
from ai.providers.native_gguf import NativeGGUFEngine
from ai.registry.models import (
    ModelCapabilityEnum,
    ModelRegistrationRequest,
    ModelTaskTypeEnum,
)
from ai.registry.registry_service import ModelRegistryService
from ai.registry.storage import ModelRegistryStorage


# ==============================================================================
# TEST FIXTURES & MODELS
# ==============================================================================

class ColorEnum(str, Enum):
    RED = "RED"
    GREEN = "GREEN"
    BLUE = "BLUE"


class SimplePrimitiveModel(BaseModel):
    name: str
    age: int
    score: float
    is_active: bool
    description: Optional[str] = None


class ComplexNestedModel(BaseModel):
    id: str
    color: ColorEnum
    status: Literal["PENDING", "APPROVED", "REJECTED"]
    tags: List[str]
    details: SimplePrimitiveModel


class ConstrainedPartModel(BaseModel):
    part_number: str = Field(pattern=r"^[0-9]{5}-[A-Z0-9]+-[0-9]{3}$")
    cost_inr: float = Field(ge=0.0, le=100000.0)
    quantity: int = Field(gt=0)


# ==============================================================================
# 1. GBNF COMPILER & CAPABILITY MATRIX TESTS
# ==============================================================================

def test_01_primitive_types_gbnf_compilation():
    """Test: Primitives (str, int, float, bool, None) compile into valid GBNF."""
    cap, reason = GBNFCompiler.can_compile(SimplePrimitiveModel)
    assert cap == GBNFCapabilityEnum.SUPPORTED

    gbnf = GBNFCompiler.compile_model(SimplePrimitiveModel)
    assert "root ::= simpleprimitivemodel" in gbnf
    assert '\\"name\\"' in gbnf
    assert '\\"age\\"' in gbnf
    assert '\\"score\\"' in gbnf
    assert '\\"is_active\\"' in gbnf
    assert "boolean" in gbnf
    assert "integer" in gbnf
    assert "number" in gbnf


def test_02_enum_and_literal_gbnf_compilation():
    """Test: Enums and Literals compile to exact choice branch rules."""
    gbnf = GBNFCompiler.compile_model(ComplexNestedModel)
    assert '"\\"RED\\"" | "\\"GREEN\\"" | "\\"BLUE\\""' in gbnf
    assert '"\\"PENDING\\"" | "\\"APPROVED\\"" | "\\"REJECTED\\""' in gbnf


def test_03_nested_objects_and_lists_compilation():
    """Test: Nested Pydantic models and list arrays compile to balanced grammar rules."""
    gbnf = GBNFCompiler.compile_model(ComplexNestedModel)
    assert "complexnestedmodel" in gbnf
    assert "details" in gbnf
    assert "[" in gbnf and "]" in gbnf
    assert "{" in gbnf and "}" in gbnf


def test_04_supported_regex_compilation():
    """Test: Supported regex patterns compile to GBNF character class sequences."""
    cap, reason = GBNFCompiler.can_compile(ConstrainedPartModel)
    assert cap == GBNFCapabilityEnum.SUPPORTED

    gbnf = GBNFCompiler.compile_model(ConstrainedPartModel)
    assert "[0-9]" in gbnf
    assert "[A-Z0-9]+" in gbnf
    assert '"-"' in gbnf


def test_05_unsupported_regex_and_union_capability_routing():
    """Test: Unsupported regex lookaheads and complex polymorphic unions are classified as UNSUPPORTED."""
    unsupported_schema = {
        "title": "UnsupportedRegexSchema",
        "type": "object",
        "properties": {
            "token": {"type": "string", "pattern": "^(?=.*[a-z]).*$"}
        }
    }
    cap, reason = GBNFCompiler.can_compile(unsupported_schema)
    assert cap == GBNFCapabilityEnum.UNSUPPORTED
    assert "unsupported regex" in reason.lower()

    with pytest.raises(UnsupportedGrammarSchemaError):
        GBNFCompiler.compile_json_schema(unsupported_schema)

    # Complex polymorphic anyOf union
    polymorphic_schema = {
        "title": "PolymorphicSchema",
        "type": "object",
        "properties": {
            "payload": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "integer"},
                    {"type": "object", "properties": {"nested": {"type": "string"}}}
                ]
            }
        }
    }
    cap_poly, reason_poly = GBNFCompiler.can_compile(polymorphic_schema)
    assert cap_poly == GBNFCapabilityEnum.UNSUPPORTED
    assert "anyof" in reason_poly.lower()


def test_06_hero_domain_schemas_compilation():
    """Test: All 5 canonical Hero domain output schemas compile successfully to GBNF."""
    domain_models = [
        IdeaDecompositionOutputSchema,
        EvidenceSynthesisOutputSchema,
        OpportunitySimulationOutputSchema,
        OpexBenchmarkingHypothesisSchema,
        ToolCallOutputSchema,
    ]
    for model_cls in domain_models:
        cap, _ = GBNFCompiler.can_compile(model_cls)
        assert cap == GBNFCapabilityEnum.SUPPORTED
        gbnf = GBNFCompiler.compile_model(model_cls)
        assert "root ::=" in gbnf
        assert "ws ::=" in gbnf
        assert "string ::=" in gbnf


@pytest.fixture
def mock_gguf_engine():
    """Sets up a loaded GGUF engine fixture."""
    temp_dir = tempfile.mkdtemp(prefix="hero_ai_10_test_")
    models_dir = os.path.join(temp_dir, "models")
    manifest_file = os.path.join(temp_dir, "registry.json")

    storage = ModelRegistryStorage(base_dir=models_dir, manifest_file=manifest_file)
    registry = ModelRegistryService(storage=storage)
    engine = NativeGGUFEngine()

    gguf_path = os.path.join(storage.models_dir, "qwen2.5-3b-test.gguf")
    with open(gguf_path, "wb") as f:
        f.write(b"GGUF\x03\x00\x00\x00mock_test_weights")

    req = ModelRegistrationRequest(
        model_id="qwen2.5-3b-test",
        display_name="Qwen 2.5 3B Test GGUF",
        file_path=gguf_path,
        primary_task_type=ModelTaskTypeEnum.GENERATION,
        capabilities=[ModelCapabilityEnum.GENERATION, ModelCapabilityEnum.STRUCTURED_OUTPUT],
        architecture="qwen2.5-3b",
        quantization="Q4_K_M",
        parameter_count="3.09B",
        context_length=4096,
        set_as_default=True,
    )
    registry.onboard_local_model(req, auto_activate_if_valid=True)
    registry.activate_model("qwen2.5-3b-test")

    return engine, registry, "qwen2.5-3b-test", temp_dir


# ==============================================================================
# 2. STRUCTURED GENERATION ENGINE EXECUTION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_07_gbnf_path_execution_success(mock_gguf_engine, monkeypatch):
    """Test: Direct GBNF grammar-constrained execution returns validated Pydantic model."""
    engine, registry, model_id, temp_dir = mock_gguf_engine
    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    structured_engine = StructuredOutputEngine(engine)
    res = await structured_engine.generate_structured(
        prompt="Decompose idea: Lightweight aluminum handlebar for Splendor Plus",
        response_model=IdeaDecompositionOutputSchema,
        allow_gbnf=True,
    )

    assert res.result is not None
    assert isinstance(res.result, IdeaDecompositionOutputSchema)
    assert res.result.category == "LIGHTWEIGHTING"
    assert res.result.target_component == "Handlebar"
    assert res.provenance.execution_path == "GBNF_GRAMMAR"
    assert res.provenance.validation_status == "VALIDATED"
    assert res.execution_envelope is not None
    assert res.execution_envelope.status == "SUCCESS"

    await engine.unload_model()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_08_fallback_path_execution_clean_json(mock_gguf_engine, monkeypatch):
    """Test: Fallback path (force_fallback=True) prompts schema and validates output."""
    engine, registry, model_id, temp_dir = mock_gguf_engine
    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    structured_engine = StructuredOutputEngine(engine)
    res = await structured_engine.generate_structured(
        prompt="Decompose idea: Aluminum handlebar for Splendor Plus",
        response_model=IdeaDecompositionOutputSchema,
        force_fallback=True,
    )

    assert res.result is not None
    assert isinstance(res.result, IdeaDecompositionOutputSchema)
    assert res.provenance.execution_path == "JSON_FALLBACK"
    assert res.provenance.validation_status == "VALIDATED"
    assert res.provenance.requires_human_review is False

    await engine.unload_model()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_09_fallback_path_retry_auto_repair(mock_gguf_engine, monkeypatch):
    """Test: Malformed JSON output is auto-repaired via error feedback retry loop."""
    engine, registry, model_id, temp_dir = mock_gguf_engine
    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    # Mock engine to return malformed JSON on attempt 1, and valid JSON on attempt 2
    attempt_count = 0

    async def flaky_generate_text(*args, **kwargs):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            return '{"category": "LIGHTWEIGHTING", "confidence_score": "INVALID_FLOAT_STRING"}'
        return json.dumps({
            "category": "LIGHTWEIGHTING",
            "target_component": "Handlebar",
            "problem_statement": "Heavy steel",
            "technical_solution": "Aluminum 6061-T6",
            "confidence_score": 0.90
        })

    monkeypatch.setattr(engine, "generate_text", flaky_generate_text)

    structured_engine = StructuredOutputEngine(engine)
    res = await structured_engine.generate_structured(
        prompt="Decompose idea",
        response_model=IdeaDecompositionOutputSchema,
        force_fallback=True,
        max_retries=2,
    )

    assert res.result is not None
    assert res.provenance.validation_attempts == 2
    assert res.provenance.validation_status == "REPAIRED"
    assert len(res.validation_errors) == 1
    assert "Attempt 1" in res.validation_errors[0]

    await engine.unload_model()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_10_persistent_failure_routes_to_human_review(mock_gguf_engine, monkeypatch):
    """Test: Persistent malformed output after max retries routes cleanly to human review."""
    engine, registry, model_id, temp_dir = mock_gguf_engine
    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    # Engine persistently outputs unparseable junk
    async def junk_generate_text(*args, **kwargs):
        return "Sorry, I cannot format this into valid JSON right now."

    monkeypatch.setattr(engine, "generate_text", junk_generate_text)

    structured_engine = StructuredOutputEngine(engine)
    res = await structured_engine.generate_structured(
        prompt="Decompose idea",
        response_model=IdeaDecompositionOutputSchema,
        force_fallback=True,
        max_retries=2,
    )

    assert res.result is None
    assert res.provenance.validation_status == "VALIDATION_FAILED"
    assert res.provenance.requires_human_review is True
    assert "Persistent schema validation failure" in (res.provenance.routing_reason or "")
    assert res.execution_envelope is not None
    assert res.execution_envelope.status == "ERROR"

    await engine.unload_model()
    shutil.rmtree(temp_dir, ignore_errors=True)


# ==============================================================================
# 3. SEMANTIC VALIDATION & FAILURE MODE TESTS
# ==============================================================================

def test_11_json_markdown_fence_stripper():
    """Test: Markdown code fences (```json ... ```) are cleanly stripped."""
    wrapped = "```json\n{\n  \"name\": \"Handlebar\",\n  \"age\": 5\n}\n```"
    cleaned = StructuredOutputEngine.extract_and_clean_json(wrapped)
    assert cleaned == '{\n  "name": "Handlebar",\n  "age": 5\n}'

    text_with_preamble = "Here is the JSON you requested:\n```\n{\"status\": \"OK\"}\n```\nHope that helps!"
    cleaned2 = StructuredOutputEngine.extract_and_clean_json(text_with_preamble)
    assert cleaned2 == '{"status": "OK"}'


@pytest.mark.asyncio
async def test_12_numeric_constraint_semantic_validation(mock_gguf_engine, monkeypatch):
    """Test: Numeric constraint violation (e.g. ge=0, gt=0) fails semantic Pydantic validation."""
    engine, registry, model_id, temp_dir = mock_gguf_engine
    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    # Engine generates negative cost (violating ge=0.0)
    async def invalid_cost_generate(*args, **kwargs):
        return json.dumps({
            "part_number": "53100-KTR-900",
            "cost_inr": -500.0,
            "quantity": 10
        })

    monkeypatch.setattr(engine, "generate_text", invalid_cost_generate)

    structured_engine = StructuredOutputEngine(engine)
    res = await structured_engine.generate_structured(
        prompt="Parse part cost",
        response_model=ConstrainedPartModel,
        force_fallback=True,
        max_retries=0,
    )

    assert res.result is None
    assert res.provenance.validation_status == "VALIDATION_FAILED"
    assert any("cost_inr" in err for err in res.validation_errors)

    await engine.unload_model()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_13_enum_violation_semantic_validation(mock_gguf_engine, monkeypatch):
    """Test: Invalid enum option fails Pydantic validation."""
    engine, registry, model_id, temp_dir = mock_gguf_engine
    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    async def invalid_enum_generate(*args, **kwargs):
        return json.dumps({
            "id": "item-01",
            "color": "PURPLE",  # Not in RED, GREEN, BLUE
            "status": "APPROVED",
            "tags": ["hero"],
            "details": {
                "name": "Part",
                "age": 2,
                "score": 4.5,
                "is_active": True
            }
        })

    monkeypatch.setattr(engine, "generate_text", invalid_enum_generate)

    structured_engine = StructuredOutputEngine(engine)
    res = await structured_engine.generate_structured(
        prompt="Get item",
        response_model=ComplexNestedModel,
        force_fallback=True,
        max_retries=0,
    )

    assert res.result is None
    assert res.provenance.validation_status == "VALIDATION_FAILED"
    assert any("color" in err for err in res.validation_errors)

    await engine.unload_model()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_14_missing_required_field_semantic_validation(mock_gguf_engine, monkeypatch):
    """Test: Missing required field fails validation."""
    engine, registry, model_id, temp_dir = mock_gguf_engine
    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    async def missing_field_generate(*args, **kwargs):
        return json.dumps({
            "category": "LIGHTWEIGHTING",
            # missing target_component, problem_statement, technical_solution
            "confidence_score": 0.8
        })

    monkeypatch.setattr(engine, "generate_text", missing_field_generate)

    structured_engine = StructuredOutputEngine(engine)
    res = await structured_engine.generate_structured(
        prompt="Decompose",
        response_model=IdeaDecompositionOutputSchema,
        force_fallback=True,
        max_retries=0,
    )

    assert res.result is None
    assert res.provenance.validation_status == "VALIDATION_FAILED"
    assert any("Field" in err for err in res.validation_errors)

    await engine.unload_model()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_15_unloaded_engine_raises_error():
    """Test: Calling generation on an unloaded engine raises RuntimeError."""
    engine = NativeGGUFEngine()
    structured_engine = StructuredOutputEngine(engine)

    with pytest.raises(RuntimeError, match="No model is currently loaded"):
        await structured_engine.generate_structured(
            prompt="Test",
            response_model=SimplePrimitiveModel,
        )


@pytest.mark.asyncio
async def test_16_provenance_cryptographic_integrity(mock_gguf_engine, monkeypatch):
    """Test: Execution envelope contains SHA-256 audit hash and accurate provenance."""
    engine, registry, model_id, temp_dir = mock_gguf_engine
    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    structured_engine = StructuredOutputEngine(engine)
    res = await structured_engine.generate_structured(
        prompt="Synthesize evidence",
        response_model=EvidenceSynthesisOutputSchema,
        allow_gbnf=True,
    )

    assert res.execution_envelope is not None
    assert len(res.execution_envelope.audit_hash) == 64
    assert res.execution_envelope.provenance.model_id == model_id
    assert res.execution_envelope.task_type == TaskType.STRUCTURED_EXTRACTION

    await engine.unload_model()
    shutil.rmtree(temp_dir, ignore_errors=True)


class StrictForbidExtraModel(BaseModel):
    model_config = {"extra": "forbid"}
    name: str
    part_id: int


@pytest.mark.asyncio
async def test_17_extra_forbidden_field_semantic_validation(mock_gguf_engine, monkeypatch):
    """Test: Unexpected extra fields fail validation when extra='forbid'."""
    engine, registry, model_id, temp_dir = mock_gguf_engine
    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    async def extra_field_generate(*args, **kwargs):
        return json.dumps({
            "name": "Brake Lever",
            "part_id": 101,
            "hallucinated_extra_field": "unauthorized_extra_value"
        })

    monkeypatch.setattr(engine, "generate_text", extra_field_generate)

    structured_engine = StructuredOutputEngine(engine)
    res = await structured_engine.generate_structured(
        prompt="Get part",
        response_model=StrictForbidExtraModel,
        force_fallback=True,
        max_retries=0,
    )

    assert res.result is None
    assert res.provenance.validation_status == "VALIDATION_FAILED"
    assert any("Extra inputs are not permitted" in err or "hallucinated_extra_field" in err for err in res.validation_errors)

    await engine.unload_model()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_18_runtime_does_not_support_grammar_routes_to_fallback(mock_gguf_engine, monkeypatch):
    """Test: When model manifest has supports_gbnf_grammar=False, engine automatically routes to fallback."""
    engine, registry, model_id, temp_dir = mock_gguf_engine
    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    # Disable GBNF in active manifest
    engine.active_manifest.supports_gbnf_grammar = False

    structured_engine = StructuredOutputEngine(engine)
    res = await structured_engine.generate_structured(
        prompt="Decompose idea",
        response_model=IdeaDecompositionOutputSchema,
        allow_gbnf=True,  # Requested GBNF, but model doesn't support it
    )

    assert res.result is not None
    assert res.provenance.execution_path == "JSON_FALLBACK"
    assert "GBNF unsupported" in (res.provenance.routing_reason or "")

    await engine.unload_model()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_19_cancellation_during_generation(mock_gguf_engine, monkeypatch):
    """Test: Cancellation aborts token generation cleanly."""
    engine, registry, model_id, temp_dir = mock_gguf_engine
    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    engine.cancel_current_generation()
    assert engine.is_loaded is True

    await engine.unload_model()
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_20_timeout_during_structured_generation(mock_gguf_engine, monkeypatch):
    """Test: Inference timeout is propagated cleanly."""
    engine, registry, model_id, temp_dir = mock_gguf_engine
    monkeypatch.setattr("ai.providers.native_gguf.model_registry_service", registry)
    await engine.load_model(model_id)

    async def slow_generate(*args, **kwargs):
        await asyncio.sleep(0.5)
        raise TimeoutError("Execution timed out after 0.1 seconds.")

    monkeypatch.setattr(engine, "generate_text", slow_generate)

    structured_engine = StructuredOutputEngine(engine)
    with pytest.raises(TimeoutError):
        await structured_engine.generate_structured(
            prompt="Slow request",
            response_model=SimplePrimitiveModel,
            timeout_seconds=0.1,
        )

    await engine.unload_model()
    shutil.rmtree(temp_dir, ignore_errors=True)
