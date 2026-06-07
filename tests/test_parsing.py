"""Tests for parsing clinical note inputs."""

from notaris.domain.parsing import parse_csv_batch, parse_text_batch


def test_parse_text_batch_empty():
    assert parse_text_batch("") == []
    assert parse_text_batch("   \n  ") == []


def test_parse_text_batch_single_note():
    notes = parse_text_batch("Patient is doing well.")
    assert len(notes) == 1
    assert notes[0].source_text == "Patient is doing well."


def test_parse_text_batch_multiple_notes():
    text = "Note 1\n\nNote 2\n\n\n\nNote 3"
    notes = parse_text_batch(text)
    assert len(notes) == 3
    assert notes[0].source_text == "Note 1"
    assert notes[1].source_text == "Note 2"
    assert notes[2].source_text == "Note 3"


def test_parse_csv_batch_empty():
    assert parse_csv_batch("") == []
    assert parse_csv_batch("   \n  ") == []


def test_parse_csv_batch_with_header():
    csv_content = (
        "id,source_text,date\n1,Patient needs a checkup,2023-01-01\n"
        "2,Patient is fine,\n3,,2023\n4,  ,"
    )
    notes = parse_csv_batch(csv_content)
    assert len(notes) == 2
    assert notes[0].source_text == "Patient needs a checkup"
    assert notes[1].source_text == "Patient is fine"


def test_parse_csv_batch_without_header():
    # If no source_text header, it should fallback to first column
    csv_content = "Patient needs a checkup,2023-01-01\nPatient is fine,\n\n  ,"
    notes = parse_csv_batch(csv_content)
    assert len(notes) == 2
    assert notes[0].source_text == "Patient needs a checkup"
    assert notes[1].source_text == "Patient is fine"
