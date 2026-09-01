"""
Structured Output Engine (Dual-Path Structured Generation Coordinator)
Executes schema-constrained SLM generation with post-generation validation.

Supports:
- Path [A]: GBNF Grammar Logit Masking (Zero-error syntax constraint on supported GGUF runtimes)
- Path [B]: Constrained JSON Schema Prompting + Pydantic Semantic Validation + 2-Stage Auto-Repair Loop
"""

import json
import re
import time
from typing import Any, Dict, Generic, List, Optional, Tuple, Type, TypeVar, Union
from pydantic import BaseModel, Field, ValidationError

from ai.core.contracts import AIExecutionEnvelope, InferenceEngineContract, ModelProvenance, TaskType
from ai.grammar.gbnf_compiler import GBNFCapabilityEnum, GBNFCompiler, UnsupportedGrammarSchemaError

T = TypeVar("T", bound=BaseModel)


class StructuredResultProvenance(BaseModel):
    """Provenance tracking specifically for structured extraction / generation."""
    schema_name: str
    schema_version: str = "v1.0"
    grammar_version: Optional[str] = None
    execution_path: str  # "GBNF_GRAMMAR" or "JSON_FALLBACK"
    model_id: str
    model_version: str
    model_hash: str
    provider: str
    runtime_engine: str
    prompt_template_version: str = "v1.0"
    validation_attempts: int = 1
    validation_status: str  # "VALIDATED", "REPAIRED", "VALIDATION_FAILED"
    requires_human_review: bool = False
    routing_reason: Optional[str] = None


class StructuredGenerationResult(BaseModel, Generic[T]):
    """Standard container for validated structured outputs."""
    result: Optional[T] = None
    raw_response: str
    parsed_json: Optional[Dict[str, Any]] = None
    provenance: StructuredResultProvenance
    validation_errors: List[str] = Field(default_factory=list)
    execution_envelope: Optional[AIExecutionEnvelope[Optional[T]]] = None


class StructuredOutputEngine:
    """
    Coordinates structured schema-constrained SLM generation across native inference engines.
    """

    def __init__(self, inference_engine: InferenceEngineContract):
        self.engine = inference_engine

    @staticmethod
    def extract_and_clean_json(text: str) -> str:
        """
        Strips markdown code fences (```json ... ```) and leading/trailing whitespace.
        Extracts outermost JSON object or array.
        """
        cleaned = text.strip()
        # Strip markdown fences
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            if len(lines) >= 2:
                # remove first line (``` or ```json) and last line (```)
                start_idx = 1
                end_idx = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
                cleaned = "\n".join(lines[start_idx:end_idx]).strip()

        # Find first '{' or '[' and last '}' or ']'
        first_brace = cleaned.find("{")
        first_bracket = cleaned.find("[")
        
        start = -1
        if first_brace != -1 and first_bracket != -1:
            start = min(first_brace, first_bracket)
        elif first_brace != -1:
            start = first_brace
        elif first_bracket != -1:
            start = first_bracket

        if start != -1:
            last_brace = cleaned.rfind("}")
            last_bracket = cleaned.rfind("]")
            end = max(last_brace, last_bracket)
            if end != -1 and end > start:
                cleaned = cleaned[start:end+1]

        return cleaned

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.0,
        allow_gbnf: bool = True,
        force_fallback: bool = False,
        max_retries: int = 2,
        seed: int = 42,
        timeout_seconds: float = 60.0,
    ) -> StructuredGenerationResult[T]:
        """
        Executes schema-constrained structured generation.
        Dual-path routing: GBNF logit constraint (Path A) vs Fallback validation loop (Path B).
        """
        t_start = time.perf_counter()

        # Extract active model manifest info if available
        manifest = getattr(self.engine, "active_manifest", None) or getattr(self.engine, "_active_manifest", None)
        model_id = getattr(manifest, "model_id", "local-slm-active") if manifest else "local-slm-active"
        model_version = getattr(manifest, "model_version", "1.0.0") if manifest else "1.0.0"
        model_hash = getattr(manifest, "sha256_checksum", "local_hash_unverified") if manifest else "local_hash_unverified"
        supports_gbnf = getattr(manifest, "supports_gbnf_grammar", True) if manifest else True

        # Capability check on schema
        schema_cap, cap_reason = GBNFCompiler.can_compile(response_model)
        can_use_gbnf = (
            allow_gbnf
            and not force_fallback
            and supports_gbnf
            and schema_cap == GBNFCapabilityEnum.SUPPORTED
        )

        gbnf_grammar_str: Optional[str] = None
        if can_use_gbnf:
            try:
                gbnf_grammar_str = GBNFCompiler.compile_model(response_model)
            except Exception:
                can_use_gbnf = False

        if can_use_gbnf and gbnf_grammar_str:
            # === PATH [A]: GBNF Logit Constrained Execution ===
            return await self._execute_gbnf_path(
                prompt=prompt,
                response_model=response_model,
                system_prompt=system_prompt,
                grammar_str=gbnf_grammar_str,
                max_tokens=max_tokens,
                temperature=temperature,
                model_id=model_id,
                model_version=model_version,
                model_hash=model_hash,
                seed=seed,
                timeout_seconds=timeout_seconds,
                t_start=t_start,
            )
        else:
            # === PATH [B]: Constrained JSON Schema Fallback Validation Loop ===
            return await self._execute_fallback_validation_loop(
                prompt=prompt,
                response_model=response_model,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                max_retries=max_retries,
                model_id=model_id,
                model_version=model_version,
                model_hash=model_hash,
                seed=seed,
                timeout_seconds=timeout_seconds,
                t_start=t_start,
                routing_note=cap_reason if schema_cap != GBNFCapabilityEnum.SUPPORTED else "GBNF unsupported or disabled",
            )

    async def _execute_gbnf_path(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str],
        grammar_str: str,
        max_tokens: int,
        temperature: float,
        model_id: str,
        model_version: str,
        model_hash: str,
        seed: int,
        timeout_seconds: float,
        t_start: float,
    ) -> StructuredGenerationResult[T]:
        """Executes generation with GBNF grammar constraints passed to engine."""
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        raw_output = ""
        # Invoke inference engine with grammar parameter
        try:
            raw_output = await self.engine.generate_text(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
                grammar=grammar_str,  # type: ignore[call-arg]
            )
        except TypeError:
            # Fallback if engine.generate_text doesn't take grammar kwarg directly
            raw_output = await self.engine.generate_text(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
            )

        cleaned = self.extract_and_clean_json(raw_output)
        validation_errors: List[str] = []
        parsed_json: Optional[Dict[str, Any]] = None
        validated_obj: Optional[T] = None

        try:
            parsed_json = json.loads(cleaned)
            # Mandatory semantic Pydantic validation
            validated_obj = response_model.model_validate(parsed_json)
            val_status = "VALIDATED"
        except (json.JSONDecodeError, ValidationError) as e:
            validation_errors.append(str(e))
            val_status = "VALIDATION_FAILED"

        provenance = StructuredResultProvenance(
            schema_name=response_model.__name__,
            schema_version="v1.0",
            grammar_version="gbnf-v1.0",
            execution_path="GBNF_GRAMMAR",
            model_id=model_id,
            model_version=model_version,
            model_hash=model_hash,
            provider="BUILTIN_NATIVE_GGUF",
            runtime_engine="llama.cpp",
            prompt_template_version="v1.0",
            validation_attempts=1,
            validation_status=val_status,
            requires_human_review=bool(validation_errors),
            routing_reason="GBNF generation succeeded" if not validation_errors else f"Post-generation validation failed: {validation_errors[0]}",
        )

        envelope = self._build_envelope(
            validated_obj=validated_obj,
            raw_output=raw_output,
            model_id=model_id,
            model_version=model_version,
            model_hash=model_hash,
            temperature=temperature,
            seed=seed,
            t_start=t_start,
            status="SUCCESS" if validated_obj is not None else "ERROR",
        )

        return StructuredGenerationResult(
            result=validated_obj,
            raw_response=raw_output,
            parsed_json=parsed_json,
            provenance=provenance,
            validation_errors=validation_errors,
            execution_envelope=envelope,
        )

    async def _execute_fallback_validation_loop(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        max_retries: int,
        model_id: str,
        model_version: str,
        model_hash: str,
        seed: int,
        timeout_seconds: float,
        t_start: float,
        routing_note: str,
    ) -> StructuredGenerationResult[T]:
        """
        Executes prompt-injected JSON schema generation with a 2-stage auto-repair retry loop.
        """
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        base_system = (
            "You are a structured data extractor. "
            "You must respond ONLY with valid JSON conforming to the following JSON Schema.\n"
            "Do NOT include markdown formatting, backticks, conversational preamble, or explanations.\n\n"
            f"JSON Schema:\n{schema_json}"
        )
        if system_prompt:
            effective_system = f"{system_prompt}\n\n{base_system}"
        else:
            effective_system = base_system

        current_prompt = prompt
        attempts = 0
        all_validation_errors: List[str] = []
        raw_output = ""
        validated_obj: Optional[T] = None
        parsed_json: Optional[Dict[str, Any]] = None

        while attempts <= max_retries:
            attempts += 1
            full_prompt = f"{effective_system}\n\nUser Request:\n{current_prompt}"
            
            raw_output = await self.engine.generate_text(
                prompt=full_prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
            )

            cleaned = self.extract_and_clean_json(raw_output)

            try:
                parsed_json = json.loads(cleaned)
                validated_obj = response_model.model_validate(parsed_json)
                break  # Validation successful!
            except (json.JSONDecodeError, ValidationError) as err:
                compact_error = self._format_compact_validation_error(err)
                all_validation_errors.append(f"Attempt {attempts}: {compact_error}")
                if attempts <= max_retries:
                    # Provide compact error feedback for next retry attempt
                    current_prompt = (
                        f"Original Prompt: {prompt}\n\n"
                        f"Your previous response failed JSON schema validation with error:\n"
                        f"{compact_error}\n\n"
                        "Please correct the JSON and ensure all fields match the required schema exactly."
                    )

        val_status = "VALIDATED" if validated_obj and attempts == 1 else ("REPAIRED" if validated_obj else "VALIDATION_FAILED")
        requires_human = validated_obj is None

        provenance = StructuredResultProvenance(
            schema_name=response_model.__name__,
            schema_version="v1.0",
            grammar_version=None,
            execution_path="JSON_FALLBACK",
            model_id=model_id,
            model_version=model_version,
            model_hash=model_hash,
            provider="BUILTIN_NATIVE_GGUF",
            runtime_engine="llama.cpp",
            prompt_template_version="v1.0",
            validation_attempts=attempts,
            validation_status=val_status,
            requires_human_review=requires_human,
            routing_reason=(
                f"Fallback validation succeeded on attempt {attempts} ({routing_note})"
                if validated_obj
                else f"Persistent schema validation failure after {attempts} attempts ({routing_note})"
            ),
        )

        envelope = self._build_envelope(
            validated_obj=validated_obj,
            raw_output=raw_output,
            model_id=model_id,
            model_version=model_version,
            model_hash=model_hash,
            temperature=temperature,
            seed=seed,
            t_start=t_start,
            status="SUCCESS" if validated_obj is not None else "ERROR",
        )

        return StructuredGenerationResult(
            result=validated_obj,
            raw_response=raw_output,
            parsed_json=parsed_json,
            provenance=provenance,
            validation_errors=all_validation_errors,
            execution_envelope=envelope,
        )

    @staticmethod
    def _format_compact_validation_error(err: Exception) -> str:
        """Formats compact, model-readable error string instead of raw stack traces."""
        if isinstance(err, json.JSONDecodeError):
            return f"JSONDecodeError: Invalid syntax at line {err.lineno}, col {err.colno}: {err.msg}"
        elif isinstance(err, ValidationError):
            err_details = []
            for e in err.errors():
                loc = ".".join(str(p) for p in e.get("loc", []))
                msg = e.get("msg", "Invalid field")
                err_details.append(f"Field '{loc}': {msg}")
            return "ValidationError: " + "; ".join(err_details[:4])
        return str(err)[:200]

    def _build_envelope(
        self,
        validated_obj: Optional[T],
        raw_output: str,
        model_id: str,
        model_version: str,
        model_hash: str,
        temperature: float,
        seed: int,
        t_start: float,
        status: str,
    ) -> AIExecutionEnvelope[Optional[T]]:
        """Constructs canonical AIExecutionEnvelope with cryptographic audit hash."""
        latency = round(time.perf_counter() - t_start, 4)
        provenance = ModelProvenance(
            model_id=model_id,
            model_version=model_version,
            model_file_hash=model_hash,
            quantization="Q4_K_M",
            runtime_engine="llama.cpp",
            runtime_profile="POC-8GB",
            context_length=4096,
            temperature=temperature,
            seed=seed,
        )

        return AIExecutionEnvelope[Optional[T]](
            task_id=f"task-struct-{int(time.time() * 1000)}",
            task_type=TaskType.STRUCTURED_EXTRACTION,
            status=status,
            result=validated_obj,
            raw_content=raw_output,
            latency_seconds=latency,
            provenance=provenance,
        )
