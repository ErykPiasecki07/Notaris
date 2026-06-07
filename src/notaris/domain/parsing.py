"""Parsing logic for input of clinical notes."""

import csv
import io
import re

from notaris.domain.models import ClinicalNote


def parse_text_batch(text: str) -> list[ClinicalNote]:
    """Parse notes separated by a double newline."""
    notes = []
    if not text.strip():
        return notes

    chunks = re.split(r"\n\s*\n", text)
    for chunk in chunks:
        stripped = chunk.strip()
        if stripped:
            notes.append(ClinicalNote(source_text=stripped))
    return notes


def parse_csv_batch(content: str) -> list[ClinicalNote]:
    """Parse notes from a CSV string"""
    notes = []
    if not content.strip():
        return notes

    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames and "source_text" in reader.fieldnames:
        for row in reader:
            text = row.get("source_text", "").strip()
            if text:
                notes.append(ClinicalNote(source_text=text))
    else:
        # Fallback to just reading first column
        reader_list = csv.reader(io.StringIO(content))
        for row in reader_list:
            if row:
                text = row[0].strip()
                if text:
                    notes.append(ClinicalNote(source_text=text))
    return notes
