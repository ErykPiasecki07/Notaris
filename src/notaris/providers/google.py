"""Google AI (Gemini) extraction provider."""

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

HttpPost = Callable[
    [str, Mapping[str, str], Mapping[str, Any], float],
    Mapping[str, Any],
]

DEFAULT_GOOGLE_MODEL = "gemini-2.0-flash"
DEFAULT_GOOGLE_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


class GoogleAIProviderError(LLMProviderError):
    """Raised when Google AI extraction cannot complete cleanly."""


class GoogleAIProvider(BaseExtractionProvider):
    """Extract values using the Google Generative Language API."""

    def __init__(
        self,
        api_key: str,
        *,
        model: str = DEFAULT_GOOGLE_MODEL,
        base_url: str = DEFAULT_GOOGLE_BASE_URL,
        timeout: float = 60.0,
        http_post: HttpPost | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("api_key is required")
        if not model.strip():
            raise ValueError("model is required")
        self.api_key = api_key.strip()
        self.model = model.strip()
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._http_post = http_post or _post_json

    def extract(
        self,
        note: ClinicalNote,
        schema: ExtractionSchema,
    ) -> ExtractionResult:
        prompt = build_extraction_prompt(note, schema)
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        url = f"{self.base_url}/models/{self.model}:generateContent"
        response = self._http_post(url, headers, payload, self.timeout)
        raw_content = _extract_text_content(response)
        try:
            return build_extraction_result(note, raw_content, schema)
        except LLMProviderError as exc:
            raise GoogleAIProviderError(str(exc)) from exc


def _extract_text_content(response: Mapping[str, Any]) -> str:
    candidates = response.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise GoogleAIProviderError("Google AI response did not include candidates")

    first_candidate = candidates[0]
    if not isinstance(first_candidate, dict):
        raise GoogleAIProviderError("Google AI candidate must be an object")

    content = first_candidate.get("content")
    if not isinstance(content, dict):
        raise GoogleAIProviderError("Google AI response did not include content")

    parts = content.get("parts")
    if not isinstance(parts, list) or not parts:
        raise GoogleAIProviderError("Google AI response did not include text content")

    first_part = parts[0]
    if not isinstance(first_part, dict):
        raise GoogleAIProviderError("Google AI content part must be an object")

    text = first_part.get("text")
    if not isinstance(text, str) or not text.strip():
        raise GoogleAIProviderError("Google AI response did not include text content")
    return text


def _post_json(
    url: str,
    headers: Mapping[str, str],
    payload: Mapping[str, Any],
    timeout: float,
) -> Mapping[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers=dict(headers),
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            decoded = response.read().decode("utf-8")
    except (HTTPError, URLError, TimeoutError) as exc:
        raise GoogleAIProviderError(f"Could not reach Google AI at {url}") from exc

    try:
        parsed = json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise GoogleAIProviderError(
            "Google AI HTTP response was not valid JSON"
        ) from exc

    if not isinstance(parsed, dict):
        raise GoogleAIProviderError("Google AI HTTP response must be a JSON object")
    return parsed
