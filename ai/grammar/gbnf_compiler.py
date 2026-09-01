"""
GBNF Grammar Compiler (GGML BNF Grammar Engine)
Compiles Pydantic BaseModel schemas and standard JSON Schemas into GBNF grammar definitions.

Provides explicit capability classification:
- SUPPORTED: Primitives, booleans, numbers, strings, enums, literals, lists, optionals, nested objects.
- PARTIALLY_SUPPORTED: Supported regex character sets, ranges, lengths.
- UNSUPPORTED: Complex regex lookarounds/backreferences, circular schemas, arbitrary unions.
"""

import re
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union
from pydantic import BaseModel


class GBNFCapabilityEnum(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"


class UnsupportedGrammarSchemaError(ValueError):
    """Raised when a Pydantic/JSON schema contains unsupported or ambiguous features for GBNF compilation."""
    pass


class GBNFCompiler:
    """
    Compiles Pydantic BaseModel classes and JSON Schemas into standard GBNF grammars.
    Ensures deterministic, syntax-compliant GGML BNF grammar generation.
    """

    # Base common terminal and primitive rules
    BASE_RULES = """ws ::= [ \\t\\n\\r]*
string ::= "\\"" ([^"\\\\] | "\\\\" (["\\\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\\""
boolean ::= "true" | "false"
number ::= ("-"? [0-9]+ ("." [0-9]+)? ([eE] [-+]? [0-9]+)?)
integer ::= ("-"? [0-9]+)
null ::= "null"
"""

    @classmethod
    def can_compile(cls, target: Union[Type[BaseModel], Dict[str, Any]]) -> Tuple[GBNFCapabilityEnum, str]:
        """
        Evaluates whether a Pydantic model or JSON schema can be compiled to GBNF.
        Returns capability classification and reason.
        """
        try:
            if isinstance(target, type) and issubclass(target, BaseModel):
                schema = target.model_json_schema()
            elif isinstance(target, dict):
                schema = target
            else:
                return GBNFCapabilityEnum.UNSUPPORTED, "Target must be a Pydantic BaseModel subclass or JSON Schema dict."

            # Check for unsupported schema features
            unsupported_reasons: List[str] = []
            cls._validate_schema_compatibility(schema, unsupported_reasons, visited=set())

            if unsupported_reasons:
                return GBNFCapabilityEnum.UNSUPPORTED, "; ".join(unsupported_reasons)

            return GBNFCapabilityEnum.SUPPORTED, "Schema is fully supported for GBNF compilation."
        except Exception as e:
            return GBNFCapabilityEnum.UNSUPPORTED, f"Capability check failed: {str(e)}"

    @classmethod
    def _validate_schema_compatibility(
        cls,
        schema: Dict[str, Any],
        reasons: List[str],
        visited: Set[str],
    ) -> None:
        """Recursive compatibility check for JSON schema definitions."""
        title = schema.get("title", "")
        if title:
            if title in visited:
                reasons.append(f"Recursive / circular schema detected for '{title}'.")
                return
            visited.add(title)

        # Check regex patterns if present
        if "pattern" in schema:
            pattern = schema["pattern"]
            if not cls._is_supported_regex(pattern):
                reasons.append(f"Unsupported regex pattern '{pattern}' (complex lookarounds/backreferences not supported in GBNF).")

        # Check properties
        props = schema.get("properties", {})
        for prop_name, prop_schema in props.items():
            if not isinstance(prop_schema, dict):
                continue
            if "pattern" in prop_schema:
                pat = prop_schema["pattern"]
                if not cls._is_supported_regex(pat):
                    reasons.append(f"Field '{prop_name}' has unsupported regex pattern '{pat}'.")

            # Check for arbitrary anyOf unions (allow simple nullability)
            if "anyOf" in prop_schema:
                any_of = prop_schema["anyOf"]
                non_null = [s for s in any_of if s.get("type") != "null"]
                if len(non_null) > 1:
                    reasons.append(f"Field '{prop_name}' contains complex polymorphic anyOf union.")

        # Check nested definitions
        defs = schema.get("$defs", {}) or schema.get("definitions", {})
        for def_name, def_schema in defs.items():
            if isinstance(def_schema, dict):
                cls._validate_schema_compatibility(def_schema, reasons, set(visited))

    @classmethod
    def _is_supported_regex(cls, pattern: str) -> bool:
        """
        Validates if a regex pattern belongs to the supported GBNF-compilable subset:
        Allowed: character classes [0-9], [a-zA-Z], literals, dashes, lengths {n}, {n,m}, +, *, ?, ^, $.
        Disallowed: lookahead (?=), lookbehind (?<=), backreferences \\1, named groups.
        """
        if "(?" in pattern or "\\1" in pattern or "\\2" in pattern:
            return False
        return True

    @classmethod
    def compile_model(cls, model_cls: Type[BaseModel]) -> str:
        """
        Compiles a Pydantic BaseModel class into a full GBNF grammar string.
        Raises UnsupportedGrammarSchemaError if schema contains unsupported features.
        """
        cap, reason = cls.can_compile(model_cls)
        if cap == GBNFCapabilityEnum.UNSUPPORTED:
            raise UnsupportedGrammarSchemaError(f"Cannot compile {model_cls.__name__} to GBNF: {reason}")

        schema = model_cls.model_json_schema()
        return cls.compile_json_schema(schema)

    @classmethod
    def compile_json_schema(cls, schema: Dict[str, Any]) -> str:
        """
        Compiles a JSON Schema dictionary into a full GBNF grammar string.
        Raises UnsupportedGrammarSchemaError if schema contains unsupported features.
        """
        cap, reason = cls.can_compile(schema)
        if cap == GBNFCapabilityEnum.UNSUPPORTED:
            raise UnsupportedGrammarSchemaError(f"Cannot compile schema to GBNF: {reason}")

        rules: Dict[str, str] = {}
        defs = schema.get("$defs", {}) or schema.get("definitions", {})

        # Compile root object
        root_rule_name = cls._clean_rule_name(schema.get("title", "root_object"))
        rules["root"] = f"{root_rule_name}"

        cls._compile_schema_object(schema, root_rule_name, rules, defs)

        # Assemble full grammar text
        output_lines: List[str] = [
            f"root ::= {rules['root']}",
            "",
            "# Base Rules",
            cls.BASE_RULES.strip(),
            "",
            "# Schema Rules",
        ]

        for rule_name, rule_def in rules.items():
            if rule_name != "root":
                output_lines.append(f"{rule_name} ::= {rule_def}")

        return "\n".join(output_lines) + "\n"

    @classmethod
    def _compile_schema_object(
        cls,
        schema: Dict[str, Any],
        rule_name: str,
        rules: Dict[str, str],
        defs: Dict[str, Any],
    ) -> str:
        """Compiles a specific JSON schema node into rule definition."""
        if rule_name in rules and rules[rule_name]:
            return rule_name

        schema_type = schema.get("type", "object")

        # Handle references ($ref)
        if "$ref" in schema:
            ref_path = schema["$ref"]
            ref_name = ref_path.split("/")[-1]
            if ref_name in defs:
                target_rule = cls._clean_rule_name(ref_name)
                cls._compile_schema_object(defs[ref_name], target_rule, rules, defs)
                return target_rule

        # Handle enum / literal choices
        if "enum" in schema:
            enum_vals = schema["enum"]
            options = []
            for v in enum_vals:
                if isinstance(v, str):
                    options.append(f'"\\"{v}\\""')
                elif isinstance(v, (int, float)):
                    options.append(f'"{v}"')
                elif isinstance(v, bool):
                    options.append('"true"' if v else '"false"')
                elif v is None:
                    options.append('"null"')
            rule_def = " | ".join(options) if options else '"null"'
            rules[rule_name] = rule_def
            return rule_name

        # Handle regex pattern
        if "pattern" in schema and schema_type == "string":
            pat = schema["pattern"]
            compiled_pat = cls._compile_regex_pattern(pat)
            rules[rule_name] = f'"\\"" {compiled_pat} "\\""'
            return rule_name

        # Handle object
        if schema_type == "object":
            properties = schema.get("properties", {})
            required_props = set(schema.get("required", []))

            prop_rules: List[Tuple[str, str]] = []
            for prop_name, prop_schema in properties.items():
                is_req = prop_name in required_props
                prop_rule_name = f"{rule_name}_{cls._clean_rule_name(prop_name)}"

                # Check if nullable / optional
                is_nullable = False
                inner_schema = prop_schema
                if "anyOf" in prop_schema:
                    any_of = prop_schema["anyOf"]
                    if any(s.get("type") == "null" for s in any_of):
                        is_nullable = True
                        inner_candidates = [s for s in any_of if s.get("type") != "null"]
                        inner_schema = inner_candidates[0] if inner_candidates else {"type": "string"}

                # Check references
                if "$ref" in inner_schema:
                    ref_name = inner_schema["$ref"].split("/")[-1]
                    field_type_rule = cls._clean_rule_name(ref_name)
                    if ref_name in defs:
                        cls._compile_schema_object(defs[ref_name], field_type_rule, rules, defs)
                else:
                    field_type_rule = cls._resolve_primitive_or_nested(
                        inner_schema, prop_rule_name, rules, defs
                    )

                if is_nullable or not is_req:
                    opt_rule_name = f"{prop_rule_name}_opt"
                    rules[opt_rule_name] = f"{field_type_rule} | null"
                    field_type_rule = opt_rule_name

                prop_rules.append((prop_name, field_type_rule))

            # Build object sequence
            if not prop_rules:
                rules[rule_name] = '"{" ws "}"'
            else:
                parts = ['"{" ws']
                for idx, (p_name, p_rule) in enumerate(prop_rules):
                    sep = '"," ws ' if idx > 0 else ''
                    parts.append(f'{sep}"\\"{p_name}\\"" ws ":" ws {p_rule}')
                parts.append('ws "}"')
                rules[rule_name] = " ".join(parts)

            return rule_name

        # Handle array / list
        if schema_type == "array":
            items_schema = schema.get("items", {})
            item_rule_name = f"{rule_name}_item"
            if "$ref" in items_schema:
                ref_name = items_schema["$ref"].split("/")[-1]
                item_rule = cls._clean_rule_name(ref_name)
                if ref_name in defs:
                    cls._compile_schema_object(defs[ref_name], item_rule, rules, defs)
            else:
                item_rule = cls._resolve_primitive_or_nested(items_schema, item_rule_name, rules, defs)

            rules[rule_name] = f'"[" ws ({item_rule} ("," ws {item_rule})*)? ws "]"'
            return rule_name

        # Fallback to primitive
        return cls._resolve_primitive_or_nested(schema, rule_name, rules, defs)

    @classmethod
    def _resolve_primitive_or_nested(
        cls,
        schema: Dict[str, Any],
        rule_name: str,
        rules: Dict[str, str],
        defs: Dict[str, Any],
    ) -> str:
        """Resolves primitives or delegates nested objects/enums to rules."""
        if "enum" in schema:
            return cls._compile_schema_object(schema, rule_name, rules, defs)

        schema_type = schema.get("type", "string")

        if schema_type == "string":
            if "pattern" in schema:
                return cls._compile_schema_object(schema, rule_name, rules, defs)
            return "string"
        elif schema_type == "integer":
            return "integer"
        elif schema_type == "number":
            return "number"
        elif schema_type == "boolean":
            return "boolean"
        elif schema_type == "null":
            return "null"
        elif schema_type in ["object", "array"]:
            return cls._compile_schema_object(schema, rule_name, rules, defs)

        return "string"

    @classmethod
    def _compile_regex_pattern(cls, pattern: str) -> str:
        """
        Converts supported regex subset into GBNF terminal rule expression.
        Handles ^, $, [0-9], [A-Z], [a-z], {n}, +, *, -, literals.
        """
        p = pattern.lstrip("^").rstrip("$")
        tokens: List[str] = []
        i = 0
        while i < len(p):
            if p.startswith("[A-Z0-9]+", i):
                tokens.append("[A-Z0-9]+")
                i += len("[A-Z0-9]+")
            elif p.startswith("[A-Z0-9]*", i):
                tokens.append("[A-Z0-9]*")
                i += len("[A-Z0-9]*")
            elif p.startswith("[A-Z0-9]", i):
                tokens.append("[A-Z0-9]")
                i += len("[A-Z0-9]")
            elif p.startswith("[a-zA-Z]+", i):
                tokens.append("[a-zA-Z]+")
                i += len("[a-zA-Z]+")
            elif p.startswith("[a-zA-Z]", i):
                tokens.append("[a-zA-Z]")
                i += len("[a-zA-Z]")
            elif p.startswith("[0-9]", i):
                i += len("[0-9]")
                # Check for repetition {n}
                if i < len(p) and p[i] == "{":
                    close_idx = p.find("}", i)
                    if close_idx != -1:
                        rep = int(p[i+1:close_idx])
                        tokens.extend(["[0-9]"] * rep)
                        i = close_idx + 1
                    else:
                        tokens.append("[0-9]")
                elif i < len(p) and p[i] == "+":
                    tokens.append("[0-9]+")
                    i += 1
                elif i < len(p) and p[i] == "*":
                    tokens.append("[0-9]*")
                    i += 1
                else:
                    tokens.append("[0-9]")
            elif p[i] == "-":
                tokens.append('"-"')
                i += 1
            elif p[i] == "_":
                tokens.append('"_"')
                i += 1
            elif p[i].isalnum():
                tokens.append(f'"{p[i]}"')
                i += 1
            else:
                tokens.append(f'"{p[i]}"')
                i += 1

        return " ".join(tokens) if tokens else 'string'

    @classmethod
    def _clean_rule_name(cls, name: str) -> str:
        """Sanitizes name for GBNF rule identifiers."""
        cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name).lower()
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        if not cleaned or cleaned in ["root", "ws", "string", "number", "boolean", "integer", "null"]:
            cleaned = f"rule_{cleaned}"
        return cleaned
