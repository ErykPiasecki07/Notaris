"""Tests for extraction CSV export route."""

import csv
import io
import json

from fastapi.testclient import TestClient

from notaris.web.app import app

client = TestClient(app)


def _seed_session(c: TestClient) -> None:
    """Post notes and schema into the session so extraction can run."""
    c.post("/notes/batch", data={"pasted_notes": "Patient age 42.\n\nPatient aged 29."})
    schema = [
        {"name": "age", "description": "Patient age", "type": "integer"},
        {"name": "diagnosis", "description": "Primary diagnosis", "type": "string"},
    ]
    c.post("/schema/new", data={"schema_data": json.dumps(schema)})


class TestExportExtractionResults:
    """GET /extraction/export."""

    def test_export_without_data_shows_error(self):
        fresh = TestClient(app)
        response = fresh.get("/extraction/export")
        assert response.status_code == 200
        assert "No extraction results available" in response.text

    def test_export_after_extraction_returns_csv(self):
        c = TestClient(app)
        _seed_session(c)
        c.post("/extraction/run")
        response = c.get("/extraction/export")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert (
            'filename="extraction_results.csv"'
            in response.headers["content-disposition"]
        )

    def test_export_body_has_expected_headers_and_rows(self):
        c = TestClient(app)
        _seed_session(c)
        c.post("/extraction/run")
        response = c.get("/extraction/export")
        reader = csv.reader(io.StringIO(response.text))
        rows = list(reader)
        assert rows[0] == ["note_id", "age", "diagnosis"]
        assert len(rows) == 3

    def test_results_page_includes_download_link(self):
        c = TestClient(app)
        _seed_session(c)
        response = c.post("/extraction/run")
        assert response.status_code == 200
        assert 'href="/extraction/export"' in response.text
        assert "Download CSV" in response.text
