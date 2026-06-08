"""Tests for shared LLM prompt and response parsing helpers."""

import pytest

from notaris.domain import ClinicalNote, ExtractionField, ExtractionSchema
from notaris.providers.llm import (
    LLMProviderError,
    build_extraction_prompt,
    parse_llm_json_content,
)


def test_build_extraction_prompt_includes_note_and_fields() -> None:
    note = ClinicalNote(source_text="Patient is 42 years old.")
    schema = ExtractionSchema(
        fields=[
            ExtractionField(name="Age", description="Age in years", type="integer"),
        ]
    )

    prompt = build_extraction_prompt(note, schema)

    assert "Patient is 42 years old." in prompt
    assert '"name": "Age"' in prompt


def test_parse_llm_json_content_accepts_top_level_values_object() -> None:
    schema = ExtractionSchema(
        fields=[
            ExtractionField(name="Age", description="Age in years", type="integer"),
            ExtractionField(
                name="Diagnosis",
                description="Primary diagnosis",
                type="string",
            ),
        ]
    )

    values = parse_llm_json_content(
        '{"values": {"Age": 42, "Diagnosis": "diabetes"}}',
        schema,
    )

    assert values == {"Age": 42, "Diagnosis": "diabetes"}


def test_parse_llm_json_content_rejects_invalid_json() -> None:
    schema = ExtractionSchema(
        fields=[
            ExtractionField(name="Age", description="Age in years", type="integer"),
        ]
    )

    with pytest.raises(LLMProviderError, match="not valid JSON"):
        parse_llm_json_content("not-json", schema)


def test_parse_llm_json_content_validates_integer_type() -> None:
    schema = ExtractionSchema(
        fields=[
            ExtractionField(name="Age", description="Age in years", type="integer"),
        ]
    )

    with pytest.raises(LLMProviderError, match="must be an integer"):
        parse_llm_json_content('{"values": {"Age": "42"}}', schema)
