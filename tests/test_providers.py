import json
from typing import Any

import pytest

from notaris.domain import ClinicalNote, ExtractionField, ExtractionSchema
from notaris.providers import (
    BaseExtractionProvider,
    MockExtractionProvider,
    OllamaProvider,
    OllamaProviderError,
)


def test_mock_provider_implements_base_interface() -> None:
    assert isinstance(MockExtractionProvider(), BaseExtractionProvider)


def test_mock_provider_returns_deterministic_values_from_note_content() -> None:
    note = ClinicalNote(
        source_text=(
            "Patient is 42 years old. Diagnosis: type 2 diabetes. "
            "HbA1c 7.8%. Medication: metformin. Outcome: improved."
        )
    )
    schema = ExtractionSchema(
        fields=[
            ExtractionField(name="Age", description="Age in years", type="integer"),
            ExtractionField(
                name="Diagnosis",
                description="Primary diagnosis",
                type="string",
            ),
            ExtractionField(
                name="HbA1c",
                description="Most recent HbA1c",
                type="number",
            ),
            ExtractionField(
                name="Medication",
                description="Medication name",
                type="string",
            ),
            ExtractionField(
                name="Outcome",
                description="Clinical outcome",
                type="string",
            ),
        ]
    )
    provider = MockExtractionProvider()

    first = provider.extract(note, schema)
    second = provider.extract(note, schema)

    assert first == second
    assert first.note == note
    assert first.values == {
        "Age": 42,
        "Diagnosis": "type 2 diabetes",
        "HbA1c": 7.8,
        "Medication": "metformin",
        "Outcome": "improved",
    }


def test_mock_provider_uses_none_for_missing_values() -> None:
    note = ClinicalNote(source_text="Synthetic note without the requested detail.")
    schema = ExtractionSchema(
        fields=[
            ExtractionField(
                name="Primary diagnosis",
                description="Primary diagnosis",
                type="string",
            )
        ]
    )

    result = MockExtractionProvider().extract(note, schema)

    assert result.values == {"Primary diagnosis": None}


def test_ollama_provider_posts_to_local_generate_endpoint() -> None:
    calls: list[tuple[str, dict[str, Any], float]] = []

    def fake_post(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        calls.append((url, payload, timeout))
        return {"response": json.dumps({"values": {"Age": 42}})}

    note = ClinicalNote(source_text="Patient is 42 years old.")
    schema = ExtractionSchema(
        fields=[
            ExtractionField(name="Age", description="Age in years", type="integer"),
        ]
    )
    provider = OllamaProvider(
        "llama3.2",
        base_url="http://localhost:11434/",
        timeout=10.0,
        http_post=fake_post,
    )

    result = provider.extract(note, schema)

    assert result.values == {"Age": 42}
    assert calls[0][0] == "http://localhost:11434/api/generate"
    assert calls[0][1]["model"] == "llama3.2"
    assert calls[0][1]["stream"] is False
    assert calls[0][1]["format"] == "json"
    assert "Patient is 42 years old." in calls[0][1]["prompt"]
    assert calls[0][2] == 10.0


def test_ollama_provider_fills_missing_requested_fields_with_none() -> None:
    def fake_post(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        return {"response": json.dumps({"values": {"Age": 42, "Extra": "ignored"}})}

    note = ClinicalNote(source_text="Patient is 42 years old.")
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

    result = OllamaProvider("llama3.2", http_post=fake_post).extract(note, schema)

    assert result.values == {"Age": 42, "Diagnosis": None}


def test_ollama_provider_rejects_invalid_model_name() -> None:
    with pytest.raises(ValueError, match="model is required"):
        OllamaProvider(" ")


def test_ollama_provider_reports_invalid_model_json() -> None:
    def fake_post(url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        return {"response": "not-json"}

    note = ClinicalNote(source_text="Patient is 42 years old.")
    schema = ExtractionSchema(
        fields=[
            ExtractionField(name="Age", description="Age in years", type="integer"),
        ]
    )

    with pytest.raises(OllamaProviderError, match="not valid JSON"):
        OllamaProvider("llama3.2", http_post=fake_post).extract(note, schema)
