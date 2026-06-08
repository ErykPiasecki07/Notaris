"""Tests for provider settings and extraction provider selection routes."""

import json

from fastapi.testclient import TestClient

from notaris.web.app import app

client = TestClient(app)


def _seed_session(c: TestClient) -> None:
    c.post("/notes/batch", data={"pasted_notes": "Patient age 42.\n\nPatient aged 29."})
    schema = [
        {"name": "age", "description": "Patient age", "type": "integer"},
        {"name": "diagnosis", "description": "Primary diagnosis", "type": "string"},
    ]
    c.post("/schema/new", data={"schema_data": json.dumps(schema)})


class TestProviderSettings:
    """Provider settings routes."""

    def test_provider_settings_page_renders(self) -> None:
        response = client.get("/extraction/provider")
        assert response.status_code == 200
        assert "Extraction Provider" in response.text
        assert "Mock (offline demo)" in response.text
        assert "Google AI (Gemini)" in response.text
        assert "Ollama (local)" in response.text

    def test_save_mock_provider_settings(self) -> None:
        response = client.post(
            "/extraction/provider",
            data={"provider": "mock"},
        )
        assert response.status_code == 200
        assert "Provider settings saved" in response.text


class TestExtractionProviderSelection:
    """Provider selection during extraction."""

    def test_default_extraction_still_uses_mock(self) -> None:
        c = TestClient(app)
        _seed_session(c)
        response = c.post("/extraction/run")
        assert response.status_code == 200
        assert "Extraction Results" in response.text
        assert "Provider: Mock (offline demo)" in response.text

    def test_google_extraction_without_api_key_shows_config_error(self) -> None:
        c = TestClient(app)
        _seed_session(c)
        response = c.post(
            "/extraction/run",
            data={"provider": "google"},
        )
        assert response.status_code == 200
        assert "Google AI requires an API key" in response.text

    def test_ollama_extraction_failure_does_not_crash_app(self) -> None:
        c = TestClient(app)
        _seed_session(c)
        response = c.post(
            "/extraction/run",
            data={
                "provider": "ollama",
                "ollama_model": "llama3.2",
                "ollama_base_url": "http://127.0.0.1:59999",
            },
        )
        assert response.status_code == 200
        assert "Extraction failed" in response.text
