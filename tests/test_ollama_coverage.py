import json
from unittest.mock import MagicMock, patch

import pytest

from notaris.domain import ClinicalNote, ExtractionField, ExtractionSchema
from notaris.providers.ollama import OllamaProvider, OllamaProviderError, _post_json


def test_ollama_default_initialization():
    provider = OllamaProvider("model")
    assert provider._http_post is _post_json


def test_ollama_missing_text_content():
    def fake_post(url, payload, timeout):
        return {"not_response": "123"}

    provider = OllamaProvider("model", http_post=fake_post)
    with pytest.raises(OllamaProviderError, match="not include text content"):
        provider.extract(
            ClinicalNote(source_text="text"),
            ExtractionSchema(
                fields=[ExtractionField(name="A", description="D", type="string")]
            ),
        )


def test_ollama_json_must_be_object():
    def fake_post(url, payload, timeout):
        return {"response": "[]"}

    provider = OllamaProvider("model", http_post=fake_post)
    with pytest.raises(OllamaProviderError, match="must be an object"):
        provider.extract(
            ClinicalNote(source_text="text"),
            ExtractionSchema(
                fields=[ExtractionField(name="A", description="D", type="string")]
            ),
        )


def test_ollama_values_must_be_object():
    def fake_post(url, payload, timeout):
        return {"response": json.dumps({"values": "string-not-dict"})}

    provider = OllamaProvider("model", http_post=fake_post)
    with pytest.raises(OllamaProviderError, match="values payload must be an object"):
        provider.extract(
            ClinicalNote(source_text="text"),
            ExtractionSchema(
                fields=[ExtractionField(name="A", description="D", type="string")]
            ),
        )


@patch("notaris.providers.ollama.urlopen")
def test_post_json_http_error(mock_urlopen):
    mock_urlopen.side_effect = TimeoutError("timeout")
    with pytest.raises(OllamaProviderError, match="Could not reach Ollama"):
        _post_json("http://a.b", {}, 1.0)


@patch("notaris.providers.ollama.urlopen")
def test_post_json_invalid_json(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"not-json"
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    with pytest.raises(OllamaProviderError, match="not valid JSON"):
        _post_json("http://a.b", {}, 1.0)


@patch("notaris.providers.ollama.urlopen")
def test_post_json_not_an_object(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.read.return_value = b"[]"
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    with pytest.raises(OllamaProviderError, match="must be a JSON object"):
        _post_json("http://a.b", {}, 1.0)
