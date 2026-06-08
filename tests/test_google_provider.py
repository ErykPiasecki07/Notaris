"""Tests for the Google AI extraction provider."""

import json
from typing import Any

import pytest

from notaris.domain import ClinicalNote, ExtractionField, ExtractionSchema
from notaris.providers.google import GoogleAIProvider, GoogleAIProviderError


def _google_response(text: str) -> dict[str, Any]:
    return {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": text}],
                }
            }
        ]
    }


def test_google_provider_posts_to_generate_content_endpoint() -> None:
    calls: list[tuple[str, dict[str, str], dict[str, Any], float]] = []

    def fake_post(
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        calls.append((url, headers, payload, timeout))
        return _google_response(json.dumps({"values": {"Age": 42}}))

    note = ClinicalNote(source_text="Patient is 42 years old.")
    schema = ExtractionSchema(
        fields=[
            ExtractionField(name="Age", description="Age in years", type="integer"),
        ]
    )
    provider = GoogleAIProvider(
        "test-key",
        model="gemini-2.0-flash",
        http_post=fake_post,
    )

    result = provider.extract(note, schema)

    assert result.values == {"Age": 42}
    assert calls[0][0].endswith("/models/gemini-2.0-flash:generateContent")
    assert calls[0][1]["x-goog-api-key"] == "test-key"
    assert calls[0][2]["generationConfig"]["responseMimeType"] == "application/json"
    assert "Patient is 42 years old." in calls[0][2]["contents"][0]["parts"][0]["text"]


def test_google_provider_fills_missing_requested_fields_with_none() -> None:
    def fake_post(
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        return _google_response(json.dumps({"values": {"Age": 42}}))

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

    result = GoogleAIProvider("test-key", http_post=fake_post).extract(note, schema)

    assert result.values == {"Age": 42, "Diagnosis": None}


def test_google_provider_rejects_invalid_api_key() -> None:
    with pytest.raises(ValueError, match="api_key is required"):
        GoogleAIProvider(" ")


def test_google_provider_reports_invalid_model_json() -> None:
    def fake_post(
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        return _google_response("not-json")

    note = ClinicalNote(source_text="Patient is 42 years old.")
    schema = ExtractionSchema(
        fields=[
            ExtractionField(name="Age", description="Age in years", type="integer"),
        ]
    )

    with pytest.raises(GoogleAIProviderError, match="not valid JSON"):
        GoogleAIProvider("test-key", http_post=fake_post).extract(note, schema)


def test_google_provider_validates_field_types() -> None:
    def fake_post(
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        return _google_response(json.dumps({"values": {"Age": "forty-two"}}))

    note = ClinicalNote(source_text="Patient is 42 years old.")
    schema = ExtractionSchema(
        fields=[
            ExtractionField(name="Age", description="Age in years", type="integer"),
        ]
    )

    with pytest.raises(GoogleAIProviderError, match="must be an integer"):
        GoogleAIProvider("test-key", http_post=fake_post).extract(note, schema)


def test_google_provider_reports_missing_candidates() -> None:
    def fake_post(
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout: float,
    ) -> dict[str, Any]:
        return {"candidates": []}

    note = ClinicalNote(source_text="Patient is 42 years old.")
    schema = ExtractionSchema(
        fields=[
            ExtractionField(name="Age", description="Age in years", type="integer"),
        ]
    )

    with pytest.raises(GoogleAIProviderError, match="did not include candidates"):
        GoogleAIProvider("test-key", http_post=fake_post).extract(note, schema)
