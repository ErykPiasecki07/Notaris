"""Tests for extraction route handlers."""

import json

from fastapi.testclient import TestClient

from notaris.web.app import app

client = TestClient(app)


def _seed_session(c: TestClient) -> None:
    """Post notes and schema into the session so extraction can run."""
    # Submit notes
    c.post("/notes/batch", data={"pasted_notes": "Patient age 42.\n\nPatient aged 29."})
    # Submit a valid schema
    schema = [
        {"name": "age", "description": "Patient age", "type": "integer"},
        {"name": "diagnosis", "description": "Primary diagnosis", "type": "string"},
    ]
    c.post("/schema/new", data={"schema_data": json.dumps(schema)})


class TestRunExtraction:
    """POST /extraction/run."""

    def test_run_without_notes_shows_error(self):
        # Fresh client with no session data
        fresh = TestClient(app)
        response = fresh.post("/extraction/run")
        assert response.status_code == 200
        assert "No notes found" in response.text

    def test_run_without_schema_shows_error(self):
        fresh = TestClient(app)
        # Submit only notes, no schema
        fresh.post(
            "/notes/batch", data={"pasted_notes": "Patient age 42.\n\nPatient aged 29."}
        )
        response = fresh.post("/extraction/run")
        assert response.status_code == 200
        assert "No schema defined" in response.text

    def test_run_successful_extraction(self):
        c = TestClient(app)
        _seed_session(c)
        response = c.post("/extraction/run")
        assert response.status_code == 200
        assert "Extraction Results" in response.text
        assert "complete" in response.text
        assert "age" in response.text
        assert "diagnosis" in response.text

    def test_result_table_has_rows(self):
        c = TestClient(app)
        _seed_session(c)
        response = c.post("/extraction/run")
        assert response.status_code == 200
        # Should contain the note index identifiers
        assert "#" in response.text
        # Two notes should produce two result rows
        assert "2 notes processed" in response.text


class TestExtractionResults:
    """GET /extraction/results."""

    def test_results_without_data_shows_error(self):
        fresh = TestClient(app)
        response = fresh.get("/extraction/results")
        assert response.status_code == 200
        assert "No extraction results available" in response.text

    def test_results_page_after_extraction(self):
        c = TestClient(app)
        _seed_session(c)
        c.post("/extraction/run")
        response = c.get("/extraction/results")
        assert response.status_code == 200
        assert "Extraction Results" in response.text
        assert "age" in response.text
