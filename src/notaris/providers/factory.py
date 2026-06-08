"""Provider configuration and factory helpers."""

import os
from enum import Enum

from pydantic import BaseModel, ConfigDict

from notaris.providers.base import BaseExtractionProvider
from notaris.providers.google import DEFAULT_GOOGLE_MODEL, GoogleAIProvider
from notaris.providers.mock import MockExtractionProvider
from notaris.providers.ollama import OllamaProvider

DEFAULT_OLLAMA_MODEL = "medgemma:4b"
DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434"


class ProviderConfigError(ValueError):
    """Raised when provider configuration is missing or invalid."""


class ProviderKind(str, Enum):
    """Supported extraction provider backends."""

    MOCK = "mock"
    GOOGLE = "google"
    OLLAMA = "ollama"


class ProviderConfig(BaseModel):
    """Session- or form-backed provider selection."""

    model_config = ConfigDict(extra="forbid")

    kind: ProviderKind = ProviderKind.MOCK
    google_api_key: str | None = None
    google_model: str = DEFAULT_GOOGLE_MODEL
    ollama_model: str = DEFAULT_OLLAMA_MODEL
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL


PROVIDER_LABELS: dict[ProviderKind, str] = {
    ProviderKind.MOCK: "Mock (offline demo)",
    ProviderKind.GOOGLE: "Google AI (Gemini)",
    ProviderKind.OLLAMA: "Ollama (local)",
}


def provider_config_from_form(
    *,
    provider: str | None = None,
    google_api_key: str | None = None,
    google_model: str | None = None,
    ollama_model: str | None = None,
    ollama_base_url: str | None = None,
) -> ProviderConfig:
    """Build provider configuration from form values."""
    kind = ProviderKind.MOCK
    if provider:
        try:
            kind = ProviderKind(provider.strip().lower())
        except ValueError as exc:
            raise ProviderConfigError(
                f"Unsupported provider '{provider}'. "
                f"Choose one of: {', '.join(kind.value for kind in ProviderKind)}."
            ) from exc

    return ProviderConfig(
        kind=kind,
        google_api_key=_empty_to_none(google_api_key),
        google_model=(google_model or DEFAULT_GOOGLE_MODEL).strip(),
        ollama_model=(ollama_model or DEFAULT_OLLAMA_MODEL).strip(),
        ollama_base_url=(ollama_base_url or DEFAULT_OLLAMA_BASE_URL).strip(),
    )


def build_provider(config: ProviderConfig) -> BaseExtractionProvider:
    """Instantiate the configured extraction provider."""
    if config.kind is ProviderKind.MOCK:
        return MockExtractionProvider()

    if config.kind is ProviderKind.GOOGLE:
        api_key = config.google_api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key or not api_key.strip():
            raise ProviderConfigError(
                "Google AI requires an API key. Enter one in the provider settings "
                "or set the GOOGLE_API_KEY environment variable."
            )
        return GoogleAIProvider(api_key=api_key.strip(), model=config.google_model)

    if config.kind is ProviderKind.OLLAMA:
        if not config.ollama_model.strip():
            raise ProviderConfigError("Ollama requires a model name.")
        return OllamaProvider(
            model=config.ollama_model.strip(),
            base_url=config.ollama_base_url.strip(),
        )

    raise ProviderConfigError(f"Unsupported provider '{config.kind.value}'.")


def provider_config_from_session(data: dict | None) -> ProviderConfig:
    """Load provider configuration stored in the demo session."""
    if not data:
        return ProviderConfig()
    return ProviderConfig.model_validate(data)


def _empty_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
