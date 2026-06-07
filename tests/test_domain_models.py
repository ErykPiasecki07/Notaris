import pytest
from pydantic import ValidationError

from notaris.domain import (
    ClinicalNote,
    ExtractionField,
    ExtractionResult,
    ExtractionSchema,
)


def test_clinical_note_accepts_source_text_and_metadata() -> None:
    note = ClinicalNote(
        source_text="Patient reports improved symptoms.",
        metadata={"source": "synthetic-demo"},
    )

    assert note.source_text == "Patient reports improved symptoms."
    assert note.metadata == {"source": "synthetic-demo"}


def test_clinical_note_rejects_empty_source_text() -> None:
    with pytest.raises(ValidationError):
        ClinicalNote(source_text="   ")


def test_extraction_field_accepts_supported_type_and_normalizes_it() -> None:
    field = ExtractionField(
        name="Outcome",
        description="Outcome at six months",
        type=" STRING ",
        constraints={"allowed_values": ["improved", "unchanged", "worse"]},
    )

    assert field.name == "Outcome"
    assert field.type == "string"
    assert field.constraints == {"allowed_values": ["improved", "unchanged", "worse"]}


def test_extraction_field_rejects_empty_name() -> None:
    with pytest.raises(ValidationError):
        ExtractionField(name="", description="Primary diagnosis", type="string")


def test_extraction_field_rejects_unsupported_type() -> None:
    with pytest.raises(ValidationError):
        ExtractionField(
            name="Diagnosis",
            description="Primary diagnosis",
            type="category",
        )


def test_extraction_schema_accepts_a_collection_of_fields() -> None:
    schema = ExtractionSchema(
        fields=[
            ExtractionField(
                name="Age",
                description="Patient age in years",
                type="integer",
            ),
            ExtractionField(
                name="HbA1c",
                description="Most recent HbA1c value",
                type="number",
            ),
        ]
    )

    assert [field.name for field in schema.fields] == ["Age", "HbA1c"]


def test_extraction_schema_rejects_duplicate_field_names() -> None:
    with pytest.raises(ValidationError):
        ExtractionSchema(
            fields=[
                ExtractionField(name="Age", description="Age in years", type="integer"),
                ExtractionField(name="Age", description="Age text", type="string"),
            ]
        )


def test_extraction_result_represents_extracted_values_for_a_note() -> None:
    note = ClinicalNote(source_text="Patient is 42 years old.")
    result = ExtractionResult(note=note, values={"Age": 42})

    assert result.note == note
    assert result.values == {"Age": 42}
