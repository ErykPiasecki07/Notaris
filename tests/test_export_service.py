"""Tests for CSV export of extraction results."""

import csv
import io

from notaris.domain.models import ClinicalNote, ExtractionResult, ExtractionSchema
from notaris.services.export import NOTE_ID_COLUMN, export_results_to_csv


def _schema() -> ExtractionSchema:
    return ExtractionSchema(
        fields=[
            {"name": "age", "description": "Patient age", "type": "integer"},
            {"name": "diagnosis", "description": "Primary diagnosis", "type": "string"},
            {
                "name": "adverse_event",
                "description": "Adverse event reported",
                "type": "boolean",
            },
        ]
    )


def _results() -> list[ExtractionResult]:
    return [
        ExtractionResult(
            note=ClinicalNote(source_text="Patient age 42."),
            values={"age": 42, "diagnosis": "Hypertension", "adverse_event": False},
        ),
        ExtractionResult(
            note=ClinicalNote(source_text="Patient aged 29."),
            values={"age": 29, "diagnosis": None, "adverse_event": True},
        ),
    ]


def _parse_csv(content: str) -> tuple[list[str], list[list[str]]]:
    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    return rows[0], rows[1:]


class TestExportResultsToCsv:
    """CSV serialization tests."""

    def test_headers_match_schema_field_names(self):
        csv_content = export_results_to_csv(_results(), _schema())
        headers, _ = _parse_csv(csv_content)
        assert headers == [NOTE_ID_COLUMN, "age", "diagnosis", "adverse_event"]

    def test_one_row_per_note(self):
        csv_content = export_results_to_csv(_results(), _schema())
        _, rows = _parse_csv(csv_content)
        assert len(rows) == 2

    def test_note_ids_are_stable_one_based_indices(self):
        csv_content = export_results_to_csv(_results(), _schema())
        _, rows = _parse_csv(csv_content)
        assert rows[0][0] == "1"
        assert rows[1][0] == "2"

    def test_values_are_serialized_correctly(self):
        csv_content = export_results_to_csv(_results(), _schema())
        _, rows = _parse_csv(csv_content)
        assert rows[0] == ["1", "42", "Hypertension", "false"]
        assert rows[1] == ["2", "29", "", "true"]

    def test_special_characters_are_quoted(self):
        results = [
            ExtractionResult(
                note=ClinicalNote(source_text="Note with comma."),
                values={
                    "age": 55,
                    "diagnosis": "Type 2, controlled",
                    "adverse_event": False,
                },
            )
        ]
        csv_content = export_results_to_csv(results, _schema())
        _, rows = _parse_csv(csv_content)
        assert rows[0][2] == "Type 2, controlled"
