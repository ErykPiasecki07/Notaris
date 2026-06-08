"""Tests for provider configuration and factory helpers."""

import os
from unittest.mock import patch

import pytest

from notaris.providers import (
    GoogleAIProvider,
    MockExtractionProvider,
    OllamaProvider,
    ProviderConfig,
    ProviderConfigError,
    ProviderKind,
    build_provider,
    provider_config_from_form,
    provider_config_from_session,
)


def test_defaults_to_mock_provider() -> None:
    provider = build_provider(ProviderConfig())
    assert isinstance(provider, MockExtractionProvider)


def test_builds_google_provider_with_form_api_key() -> None:
    config = ProviderConfig(
        kind=ProviderKind.GOOGLE,
        google_api_key="test-key",
        google_model="gemini-2.0-flash",
    )
    provider = build_provider(config)
    assert isinstance(provider, GoogleAIProvider)
    assert provider.api_key == "test-key"
    assert provider.model == "gemini-2.0-flash"


def test_builds_google_provider_from_environment() -> None:
    config = ProviderConfig(kind=ProviderKind.GOOGLE)
    with patch.dict(os.environ, {"GOOGLE_API_KEY": "env-key"}):
        provider = build_provider(config)
    assert isinstance(provider, GoogleAIProvider)
    assert provider.api_key == "env-key"


def test_google_provider_requires_api_key() -> None:
    config = ProviderConfig(kind=ProviderKind.GOOGLE)
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("GOOGLE_API_KEY", None)
        with pytest.raises(ProviderConfigError, match="API key"):
            build_provider(config)


def test_builds_ollama_provider() -> None:
    config = ProviderConfig(
        kind=ProviderKind.OLLAMA,
        ollama_model="llama3.2",
        ollama_base_url="http://localhost:11434",
    )
    provider = build_provider(config)
    assert isinstance(provider, OllamaProvider)
    assert provider.model == "llama3.2"
    assert provider.base_url == "http://localhost:11434"


def test_provider_config_from_form_rejects_unknown_provider() -> None:
    with pytest.raises(ProviderConfigError, match="Unsupported provider"):
        provider_config_from_form(provider="unknown")


def test_provider_config_from_session_defaults_to_mock() -> None:
    config = provider_config_from_session(None)
    assert config.kind is ProviderKind.MOCK


def test_provider_config_round_trip_through_session_dict() -> None:
    original = ProviderConfig(
        kind=ProviderKind.OLLAMA,
        ollama_model="mistral",
    )
    restored = provider_config_from_session(original.model_dump())
    assert restored == original
