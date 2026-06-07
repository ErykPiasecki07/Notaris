"""Typed domain models for clinical note extraction."""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SUPPORTED_FIELD_TYPES = frozenset({"string", "integer", "number", "boolean", "date"})


def _require_non_empty(value: str, field_label: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_label} is required")
    return stripped


class ClinicalNote(BaseModel):
    """Source text and optional metadata for one clinical note."""

    model_config = ConfigDict(extra="forbid")

    source_text: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_text")
    @classmethod
    def source_text_must_not_be_empty(cls, value: str) -> str:
        return _require_non_empty(value, "source_text")


class ExtractionField(BaseModel):
    """One field requested by a study-specific extraction schema."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    type: str
    constraints: Optional[dict[str, Any]] = None

    @field_validator("name")
    @classmethod
    def name_must_not_be_empty(cls, value: str) -> str:
        return _require_non_empty(value, "name")

    @field_validator("description")
    @classmethod
    def description_must_not_be_empty(cls, value: str) -> str:
        return _require_non_empty(value, "description")

    @field_validator("type")
    @classmethod
    def type_must_be_supported(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in SUPPORTED_FIELD_TYPES:
            supported_types = ", ".join(sorted(SUPPORTED_FIELD_TYPES))
            raise ValueError(f"type must be one of: {supported_types}")
        return normalized


class ExtractionSchema(BaseModel):
    """A study-specific collection of fields to extract."""

    model_config = ConfigDict(extra="forbid")

    fields: list[ExtractionField] = Field(min_length=1)

    @model_validator(mode="after")
    def field_names_must_be_unique(self) -> "ExtractionSchema":
        names = [field.name for field in self.fields]
        if len(set(names)) != len(names):
            raise ValueError("field names must be unique")
        return self


class ExtractionResult(BaseModel):
    """Extracted values for a source note."""

    model_config = ConfigDict(extra="forbid")

    note: ClinicalNote
    values: dict[str, Any]
