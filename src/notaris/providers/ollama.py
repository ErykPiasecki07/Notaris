"""Ollama-backed local LLM extraction provider."""

import json
from collections.abc import Callable, Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from notaris.domain import ClinicalNote, ExtractionResult, ExtractionSchema
from notaris.providers.base import BaseExtractionProvider

HttpPost = Callable[[str, Mapping[str, Any], float], Mapping[str, Any]]


class OllamaProviderError(RuntimeError):
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
            "prompt": self._build_prompt(note, schema),
            "stream": False,
            "format": "json",
        }
        response = self._http_post(
            f"{self.base_url}/api/generate",
            payload,
            self.timeout,
        )
        values = self._parse_response(response, schema)
        return ExtractionResult(note=note, values=values)

    def _build_prompt(self, note: ClinicalNote, schema: ExtractionSchema) -> str:
        fields = [
            {
                "name": field.name,
                "description": field.description,
                "type": field.type,
                "constraints": field.constraints,
            }
            for field in schema.fields
        ]
        return (
            "Extract structured research values from the clinical note. "
            "Return only JSON with a top-level object named values. "
            "The values object must include exactly the requested field names. "
            "Use null when a value is not present.\n\n"
            f"Fields:\n{json.dumps(fields, indent=2)}\n\n"
            f"Clinical note:\n{note.source_text}"
        )

    def _parse_response(
        self,
        response: Mapping[str, Any],
        schema: ExtractionSchema,
    ) -> dict[str, Any]:
        raw_content = response.get("response")
        if not isinstance(raw_content, str):
            raise OllamaProviderError("Ollama response did not include text content")

        try:
            parsed = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise OllamaProviderError("Ollama response was not valid JSON") from exc

        if not isinstance(parsed, dict):
            raise OllamaProviderError("Ollama JSON response must be an object")

        raw_values = parsed.get("values", parsed)
        if not isinstance(raw_values, dict):
            raise OllamaProviderError("Ollama values payload must be an object")

        requested_names = [field.name for field in schema.fields]
        return {name: raw_values.get(name) for name in requested_names}


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
