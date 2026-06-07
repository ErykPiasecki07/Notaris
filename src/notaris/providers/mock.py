"""Deterministic local extraction provider for demos and tests."""

import re
from datetime import date
from typing import Any

from notaris.domain import (
    ClinicalNote,
    ExtractionField,
    ExtractionResult,
    ExtractionSchema,
)
from notaris.providers.base import BaseExtractionProvider


class MockExtractionProvider(BaseExtractionProvider):
    """Extract predictable values without API keys, network access, or real data."""

    def extract(
        self,
        note: ClinicalNote,
        schema: ExtractionSchema,
    ) -> ExtractionResult:
        values = {
            field.name: self._extract_field_value(field, note.source_text)
            for field in schema.fields
        }
        return ExtractionResult(note=note, values=values)

    def _extract_field_value(self, field: ExtractionField, source_text: str) -> Any:
        normalized_name = _normalize(field.name)
        normalized_text = _normalize(source_text)

        if field.type == "integer":
            return self._extract_integer(normalized_name, source_text)
        if field.type == "number":
            return self._extract_number(normalized_name, source_text)
        if field.type == "boolean":
            return self._extract_boolean(normalized_name, normalized_text)
        if field.type == "date":
            return self._extract_date(source_text)
        return self._extract_string(normalized_name, source_text)

    def _extract_integer(self, field_name: str, source_text: str) -> int | None:
        if "age" in field_name:
            age_pattern = (
                r"\b(?:age(?:d)?|patient is)\s*(\d{1,3})\b|"
                r"\b(\d{1,3})\s*years?\s*old\b"
            )
            match = re.search(
                age_pattern,
                source_text,
                re.IGNORECASE,
            )
            if match:
                return int(next(group for group in match.groups() if group is not None))
        match = re.search(r"\b\d+\b", source_text)
        return int(match.group(0)) if match else None

    def _extract_number(self, field_name: str, source_text: str) -> float | None:
        if "hba1c" in field_name or "a1c" in field_name:
            match = re.search(
                r"\b(?:hba1c|a1c)\D{0,12}(\d+(?:\.\d+)?)",
                source_text,
                re.IGNORECASE,
            )
            if match:
                return float(match.group(1))
        match = re.search(r"\b\d+(?:\.\d+)?\b", source_text)
        return float(match.group(0)) if match else None

    def _extract_boolean(self, field_name: str, normalized_text: str) -> bool | None:
        positive_markers = ("yes", "present", "positive", "reports", "noted")
        negative_markers = ("no ", "denies", "negative", "absent", "none")

        if "adverse" in field_name or "event" in field_name:
            if any(marker in normalized_text for marker in negative_markers):
                return False
            if "adverse" in normalized_text or "side effect" in normalized_text:
                return True

        if any(marker in normalized_text for marker in negative_markers):
            return False
        if any(marker in normalized_text for marker in positive_markers):
            return True
        return None

    def _extract_date(self, source_text: str) -> str | None:
        iso_match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", source_text)
        if iso_match:
            return iso_match.group(0)

        us_match = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", source_text)
        if us_match:
            month, day, year = (int(part) for part in us_match.groups())
            try:
                return date(year, month, day).isoformat()
            except ValueError:
                return None
        return None

    def _extract_string(self, field_name: str, source_text: str) -> str | None:
        patterns = {
            "diagnosis": r"\bdiagnosis(?: is|:)?\s*([^.;\n]+)",
            "drug": r"\b(?:drug|medication)(?: is|:)?\s*([^.;\n]+)",
            "medication": r"\b(?:drug|medication)(?: is|:)?\s*([^.;\n]+)",
            "dose": r"\b(?:dose|dosage)(?: is|:)?\s*([^.;\n]+)",
            "outcome": r"\boutcome(?: is|:)?\s*([^.;\n]+)",
            "follow": r"\bfollow-?up(?: is|:)?\s*([^.;\n]+)",
        }
        for marker, pattern in patterns.items():
            if marker in field_name:
                match = re.search(pattern, source_text, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
        return None


def _normalize(value: str) -> str:
    return " ".join(value.lower().split())
