"""Tests for schema extraction routes."""

import json

from fastapi.testclient import TestClient

from notaris.web.app import app

client = TestClient(app)


def test_schema_builder_page_renders():
    response = client.get("/schema/new")
    assert response.status_code == 200
    assert "Define Extraction Schema" in response.text
    assert "+ Add Field" in response.text


def test_schema_builder_post_valid():
    valid_schema = [
        {"name": "age", "description": "Patient age", "type": "integer"},
        {"name": "diagnosis", "description": "Primary diagnosis", "type": "string"},
    ]
    response = client.post(
        "/schema/new", data={"schema_data": json.dumps(valid_schema)}
    )
    assert response.status_code == 200
    assert "Schema Configuration Saved" in response.text
    assert "age" in response.text
    assert "Patient age" in response.text
    assert "integer" in response.text


def test_schema_builder_post_invalid_model():
    invalid_schema = [
        {"name": "", "description": "Patient age", "type": "integer"},
    ]
    response = client.post(
        "/schema/new", data={"schema_data": json.dumps(invalid_schema)}
    )
    assert response.status_code == 200
    assert "Field error:" in response.text
    assert "name is required" in response.text


def test_schema_builder_post_invalid_json():
    response = client.post("/schema/new", data={"schema_data": "not valid json"})
    assert response.status_code == 200
    assert (
        "Expecting value" in response.text
        or "JSON structure" in response.text
        or "json" in response.text.lower()
    )
