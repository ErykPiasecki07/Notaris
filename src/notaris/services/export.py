"""CSV export for extraction results."""

import csv
import io
from typing import Any

from notaris.domain.models import ExtractionResult, ExtractionSchema

NOTE_ID_COLUMN = "note_id"


def _format_cell_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def export_results_to_csv(
    results: list[ExtractionResult],
    schema: ExtractionSchema,
) -> str:
    """Serialize extraction results as a CSV string.

    Produces one row per note with a stable 1-based ``note_id`` and one
    column per schema field in schema definition order.
    """
    field_names = [field.name for field in schema.fields]
    headers = [NOTE_ID_COLUMN, *field_names]

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)

    for idx, result in enumerate(results):
        row: list[Any] = [idx + 1]
        for name in field_names:
            row.append(_format_cell_value(result.values.get(name)))
        writer.writerow(row)

    return buffer.getvalue()
