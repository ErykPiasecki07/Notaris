"""Tests for batch input routes."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from notaris.web.app import app

client = TestClient(app)


def test_batch_input_form_renders():
    response = client.get("/notes/batch")
    assert response.status_code == 200
    assert "Batch Input Notes" in response.text
    assert "<form" in response.text


def test_post_batch_input_empty():
    response = client.post("/notes/batch", data={"pasted_notes": "   "})
    assert response.status_code == 200
    assert "Please provide notes either by pasting" in response.text


def test_post_batch_input_pasted_notes():
    response = client.post("/notes/batch", data={"pasted_notes": "Note 1\n\nNote 2"})
    assert response.status_code == 200
    assert "Successfully parsed 2 notes." in response.text
    assert "Note 1" in response.text
    assert "Note 2" in response.text


def test_post_batch_input_pasted_notes_empty_result():
    response = client.post("/notes/batch", data={"pasted_notes": "\n\n"})
    assert response.status_code == 200
    assert "Please provide notes either by pasting" in response.text


def test_post_batch_input_upload_empty_csv():
    # A CSV where the first column is empty will result in no parsed notes,
    # but the string isn't totally empty (it has commas and newlines)
    file_content = b", \n , \n"
    response = client.post(
        "/notes/batch", files={"upload_file": ("notes.csv", file_content, "text/csv")}
    )
    assert response.status_code == 200
    assert "No valid notes found in the input" in response.text


def test_post_batch_input_upload_text_file():
    file_content = b"Note A\n\nNote B\n\nNote C"
    response = client.post(
        "/notes/batch", files={"upload_file": ("notes.txt", file_content, "text/plain")}
    )
    assert response.status_code == 200
    assert "Successfully parsed 3 notes." in response.text
    assert "Note A" in response.text
    assert "Note B" in response.text
    assert "Note C" in response.text


def test_post_batch_input_upload_csv_file():
    file_content = b"source_text\nCSV Note 1\nCSV Note 2\n"
    response = client.post(
        "/notes/batch", files={"upload_file": ("notes.csv", file_content, "text/csv")}
    )
    assert response.status_code == 200
    assert "Successfully parsed 2 notes." in response.text
    assert "CSV Note 1" in response.text
    assert "CSV Note 2" in response.text


def test_post_batch_input_upload_csv_file_invalid():
    # If standard csv parsing doesn't crash on this, it'll just parse 0 notes.
    # We test the empty file logic here
    file_content = b""
    response = client.post(
        "/notes/batch", files={"upload_file": ("notes.csv", file_content, "text/csv")}
    )
    assert response.status_code == 200
    assert (
        "No valid notes found in the input" in response.text
        or "Please provide notes either" in response.text
    )


def test_post_batch_input_upload_read_exception():
    with patch(
        "starlette.datastructures.UploadFile.read", new_callable=AsyncMock
    ) as mock_read:
        mock_read.side_effect = Exception("Read error")
        response = client.post(
            "/notes/batch", files={"upload_file": ("notes.csv", b"dummy", "text/csv")}
        )
        assert response.status_code == 200
        assert "Failed to read the uploaded file." in response.text


def test_post_batch_input_upload_csv_parse_exception():
    with patch(
        "notaris.web.routes.parse_csv_batch", side_effect=Exception("Parse err")
    ):
        response = client.post(
            "/notes/batch", files={"upload_file": ("notes.csv", b"dummy", "text/csv")}
        )
        assert response.status_code == 200
        assert "Failed to parse CSV file." in response.text
