"""Shared prompt building and response parsing for LLM extraction providers."""

import json
from typing import Any

from notaris.domain import ClinicalNote, ExtractionResult, ExtractionSchema
from notaris.domain.models import SUPPORTED_FIELD_TYPES


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider cannot complete extraction cleanly."""


def build_extraction_prompt(note: ClinicalNote, schema: ExtractionSchema) -> str:
    """Build a provider-agnostic extraction prompt for one note and schema."""
    fields = [
        {
            "name": field.name,
            "description": field.description,
            "type": field.type,
            "constraints": field.constraints,
        }
        for field in schema.fields
    ]
    return (
        "Extract structured research values from the clinical note. "
        "Return only JSON with a top-level object named values. "
        "The values object must include exactly the requested field names. "
        "Use null when a value is not present.\n\n"
        f"Fields:\n{json.dumps(fields, indent=2)}\n\n"
        f"Clinical note:\n{note.source_text}"
    )


def parse_llm_json_content(
    raw_content: str,
    schema: ExtractionSchema,
) -> dict[str, Any]:
    """Parse and validate JSON content returned by an LLM."""
    try:
        parsed = json.loads(raw_content)
    except json.JSONDecodeError as exc:
        raise LLMProviderError("LLM response was not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise LLMProviderError("LLM JSON response must be an object")

    raw_values = parsed.get("values", parsed)
    if not isinstance(raw_values, dict):
        raise LLMProviderError("LLM values payload must be an object")

    requested_names = [field.name for field in schema.fields]
    values = {name: raw_values.get(name) for name in requested_names}
    return validate_extraction_values(values, schema)


def validate_extraction_values(
    values: dict[str, Any],
    schema: ExtractionSchema,
) -> dict[str, Any]:
    """Validate extracted values against schema field types."""
    validated: dict[str, Any] = {}
    fields_by_name = {field.name: field for field in schema.fields}

    for name, value in values.items():
        field = fields_by_name.get(name)
        if field is None:
            continue
        if value is None:
            validated[name] = None
            continue
        validated[name] = _coerce_value(value, field.type, name)

    return validated


def build_extraction_result(
    note: ClinicalNote,
    raw_content: str,
    schema: ExtractionSchema,
) -> ExtractionResult:
    """Parse LLM output and return a validated ``ExtractionResult``."""
    values = parse_llm_json_content(raw_content, schema)
    return ExtractionResult(note=note, values=values)


def _coerce_value(value: Any, field_type: str, field_name: str) -> Any:
    if field_type == "string":
        if not isinstance(value, str):
            raise LLMProviderError(f"Field '{field_name}' must be a string")
        return value

    if field_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise LLMProviderError(f"Field '{field_name}' must be an integer")
        return value

    if field_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise LLMProviderError(f"Field '{field_name}' must be a number")
        return float(value) if isinstance(value, float) else value

    if field_type == "boolean":
        if not isinstance(value, bool):
            raise LLMProviderError(f"Field '{field_name}' must be a boolean")
        return value

    if field_type == "date":
        if not isinstance(value, str):
            raise LLMProviderError(f"Field '{field_name}' must be a date string")
        return value

    supported_types = ", ".join(sorted(SUPPORTED_FIELD_TYPES))
    raise LLMProviderError(f"Unsupported field type. Must be one of: {supported_types}")
