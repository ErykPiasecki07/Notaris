"""Tests for the batch extraction service."""

import pytest

from notaris.domain.models import ClinicalNote, ExtractionSchema
from notaris.providers.mock import MockExtractionProvider
from notaris.services.extraction import (
    BatchExtractionService,
    ExtractionRunStatus,
)


def _notes() -> list[ClinicalNote]:
    """Return a minimal batch of two clinical notes."""
    return [
        ClinicalNote(source_text="Patient age 42. Diagnosis: Hypertension."),
        ClinicalNote(source_text="Patient aged 29. Denies adverse events."),
    ]


def _schema() -> ExtractionSchema:
    """Return a simple extraction schema."""
    return ExtractionSchema(
        fields=[
            {"name": "age", "description": "Patient age", "type": "integer"},
            {
                "name": "diagnosis",
                "description": "Primary diagnosis",
                "type": "string",
            },
            {
                "name": "adverse_event",
                "description": "Adverse event reported",
                "type": "boolean",
            },
        ]
    )


class TestBatchExtractionService:
    """Core service behaviour tests."""

    def test_defaults_to_mock_provider(self):
        service = BatchExtractionService()
        assert isinstance(service._provider, MockExtractionProvider)

    def test_initial_status_is_pending(self):
        service = BatchExtractionService()
        assert service.status == ExtractionRunStatus.PENDING

    def test_run_produces_one_result_per_note(self):
        service = BatchExtractionService()
        results = service.run(_notes(), _schema())
        assert len(results) == 2

    def test_status_is_complete_after_run(self):
        service = BatchExtractionService()
        service.run(_notes(), _schema())
        assert service.status == ExtractionRunStatus.COMPLETE

    def test_results_contain_expected_keys(self):
        service = BatchExtractionService()
        results = service.run(_notes(), _schema())
        for result in results:
            assert "age" in result.values
            assert "diagnosis" in result.values
            assert "adverse_event" in result.values

    def test_extracted_values_are_deterministic(self):
        service = BatchExtractionService()
        results = service.run(_notes(), _schema())
        # First note: "Patient age 42"
        assert results[0].values["age"] == 42
        assert results[0].values["diagnosis"] == "Hypertension"

    def test_results_property_returns_copy(self):
        service = BatchExtractionService()
        service.run(_notes(), _schema())
        r1 = service.results
        r2 = service.results
        assert r1 is not r2
        assert r1 == r2

    def test_run_with_empty_notes_raises(self):
        service = BatchExtractionService()
        with pytest.raises(ValueError, match="At least one clinical note"):
            service.run([], _schema())

    def test_error_is_none_after_successful_run(self):
        service = BatchExtractionService()
        service.run(_notes(), _schema())
        assert service.error is None

    def test_accepts_custom_provider(self):
        provider = MockExtractionProvider()
        service = BatchExtractionService(provider=provider)
        assert service._provider is provider


class TestBatchExtractionServiceTableOutput:
    """Tests for the table-reshape helper."""

    def test_table_has_correct_columns(self):
        service = BatchExtractionService()
        schema = _schema()
        service.run(_notes(), schema)
        table = service.results_as_table(schema)
        assert table["columns"] == ["age", "diagnosis", "adverse_event"]

    def test_table_has_one_row_per_note(self):
        service = BatchExtractionService()
        schema = _schema()
        service.run(_notes(), schema)
        table = service.results_as_table(schema)
        assert len(table["rows"]) == 2

    def test_table_rows_include_note_index(self):
        service = BatchExtractionService()
        schema = _schema()
        service.run(_notes(), schema)
        table = service.results_as_table(schema)
        assert table["rows"][0]["_note_index"] == 1
        assert table["rows"][1]["_note_index"] == 2

    def test_table_rows_include_extracted_values(self):
        service = BatchExtractionService()
        schema = _schema()
        service.run(_notes(), schema)
        table = service.results_as_table(schema)
        assert table["rows"][0]["age"] == 42
        assert table["rows"][0]["diagnosis"] == "Hypertension"


class TestBatchExtractionServiceFailure:
    """Tests for failure / error state handling."""

    def test_status_is_failed_on_provider_error(self):
        class FailingProvider(MockExtractionProvider):
            def extract(self, note, schema):
                raise RuntimeError("boom")

        service = BatchExtractionService(provider=FailingProvider())
        with pytest.raises(RuntimeError, match="boom"):
            service.run(_notes(), _schema())
        assert service.status == ExtractionRunStatus.FAILED
        assert service.error == "boom"
