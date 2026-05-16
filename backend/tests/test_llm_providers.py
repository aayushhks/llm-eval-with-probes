"""Tests for the LLM provider abstraction. Mock-only — no live API calls."""

from __future__ import annotations

import pytest

from app.services.llm.mock_provider import MockProvider
from app.services.llm.registry import get_provider
from app.services.llm.types import LLMRequest, Message, ProviderName


@pytest.mark.asyncio
async def test_mock_provider_returns_structured_response() -> None:
    provider = MockProvider(canned_response="hello")
    request = LLMRequest(
        messages=[
            Message(role="system", content="be terse"),
            Message(role="user", content="say hi"),
        ],
        model="mock-model",
    )

    response = await provider.complete(request)

    assert response.provider == ProviderName.MOCK
    assert response.model == "mock-model"
    assert "hello" in response.content
    assert "say hi" in response.content
    assert response.usage.completion_tokens > 0
    assert response.latency_ms >= 0
    assert response.finish_reason == "stop"


@pytest.mark.asyncio
async def test_registry_returns_mock_provider() -> None:
    provider = get_provider(ProviderName.MOCK)
    assert provider.name == ProviderName.MOCK


def test_registry_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("nonexistent")  # type: ignore[arg-type]
