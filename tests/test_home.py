"""Tests for the homepage."""

from fastapi.testclient import TestClient

from notaris.web.app import app

client = TestClient(app)


def test_homepage_renders():
    response = client.get("/")
    assert response.status_code == 200
    assert "Notaris - Clinical Note Data Extraction" in response.text
    assert "Accelerate Clinical Research" in response.text
    assert "Start New Extraction" in response.text
