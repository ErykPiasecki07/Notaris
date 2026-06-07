"""Batch extraction application service.

Keeps extraction orchestration outside route handlers so the logic is
testable, reusable, and independent of the web layer.
"""

from enum import Enum
from typing import Any

from notaris.domain.models import ClinicalNote, ExtractionResult, ExtractionSchema
from notaris.providers.base import BaseExtractionProvider
from notaris.providers.mock import MockExtractionProvider


class ExtractionRunStatus(str, Enum):
    """Simple status tracker for an in-process demo extraction run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class BatchExtractionService:
    """Orchestrate extraction across a batch of clinical notes.

    Accepts a provider to enable swapping between mock and real
    implementations without changing calling code.
    """

    def __init__(self, provider: BaseExtractionProvider | None = None) -> None:
        self._provider = provider or MockExtractionProvider()
        self._status: ExtractionRunStatus = ExtractionRunStatus.PENDING
        self._results: list[ExtractionResult] = []
        self._error: str | None = None

    @property
    def status(self) -> ExtractionRunStatus:
        return self._status

    @property
    def results(self) -> list[ExtractionResult]:
        return list(self._results)

    @property
    def error(self) -> str | None:
        return self._error

    def run(
        self,
        notes: list[ClinicalNote],
        schema: ExtractionSchema,
    ) -> list[ExtractionResult]:
        """Execute extraction for every note in the batch.

        Returns one ``ExtractionResult`` per note.  Updates internal
        status so callers can track progress for the demo flow.
        """
        if not notes:
            raise ValueError("At least one clinical note is required.")

        self._status = ExtractionRunStatus.RUNNING
        self._results = []
        self._error = None

        try:
            for note in notes:
                result = self._provider.extract(note, schema)
                self._results.append(result)
            self._status = ExtractionRunStatus.COMPLETE
        except Exception as exc:
            self._status = ExtractionRunStatus.FAILED
            self._error = str(exc)
            raise

        return list(self._results)

    def results_as_table(self, schema: ExtractionSchema) -> dict[str, Any]:
        """Reshape results into a table-friendly structure.

        Returns a dict with ``columns`` (list of field names) and
        ``rows`` (list of dicts, one per note).
        """
        columns = [field.name for field in schema.fields]
        rows: list[dict[str, Any]] = []

        for idx, result in enumerate(self._results):
            row: dict[str, Any] = {"_note_index": idx + 1}
            for col in columns:
                row[col] = result.values.get(col)
            rows.append(row)

        return {"columns": columns, "rows": rows}
