"""Abstract LLM provider protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.services.llm.types import LLMRequest, LLMResponse, ProviderName


@runtime_checkable
class LLMProvider(Protocol):
    """All providers must implement this interface."""

    name: ProviderName

    async def complete(self, request: LLMRequest) -> LLMResponse:
        """Send a chat completion request and return a structured response."""
        ...
