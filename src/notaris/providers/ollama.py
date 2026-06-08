"""Ollama-backed local LLM extraction provider."""

import json
from collections.abc import Callable, Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from notaris.domain import ClinicalNote, ExtractionResult, ExtractionSchema
from notaris.providers.base import BaseExtractionProvider
from notaris.providers.llm import (
    LLMProviderError,
    build_extraction_prompt,
    build_extraction_result,
)

HttpPost = Callable[[str, Mapping[str, Any], float], Mapping[str, Any]]


class OllamaProviderError(LLMProviderError):
    """Raised when Ollama extraction cannot complete cleanly."""


class OllamaProvider(BaseExtractionProvider):
    """Extract values using a local Ollama model."""

    def __init__(
        self,
        model: str,
        *,
        base_url: str = "http://127.0.0.1:11434",
        timeout: float = 60.0,
        http_post: HttpPost | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("model is required")
        self.model = model.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._http_post = http_post or _post_json

    def extract(
        self,
        note: ClinicalNote,
        schema: ExtractionSchema,
    ) -> ExtractionResult:
        payload = {
            "model": self.model,
            "prompt": build_extraction_prompt(note, schema),
            "stream": False,
            "format": "json",
        }
        response = self._http_post(
            f"{self.base_url}/api/generate",
            payload,
            self.timeout,
        )
        raw_content = response.get("response")
        if not isinstance(raw_content, str):
            raise OllamaProviderError("Ollama response did not include text content")

        try:
            return build_extraction_result(note, raw_content, schema)
        except LLMProviderError as exc:
            raise OllamaProviderError(str(exc)) from exc


def _post_json(
    url: str,
    payload: Mapping[str, Any],
    timeout: float,
) -> Mapping[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            decoded = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise OllamaProviderError(f"Could not reach Ollama at {url}") from exc

    try:
        parsed = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise OllamaProviderError("Ollama HTTP response was not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise OllamaProviderError("Ollama HTTP response must be a JSON object")
    return parsed
