"""Shared types for the LLM provider abstraction."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ProviderName(StrEnum):
    GROQ = "groq"
    GEMINI = "gemini"
    MOCK = "mock"


class Message(BaseModel):
    role: str = Field(description="system, user, or assistant")
    content: str


class LLMRequest(BaseModel):
    """Provider-agnostic request payload."""

    messages: list[Message]
    model: str
    temperature: float = 0.0
    max_tokens: int = 1024
    response_format: dict[str, Any] | None = Field(
        default=None,
        description="Optional JSON schema for structured output (provider-dependent).",
    )
    seed: int | None = None


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    """Provider-agnostic response."""

    provider: ProviderName
    model: str
    content: str
    usage: TokenUsage
    latency_ms: int
    finish_reason: str | None = None
    raw_response: dict[str, Any] = Field(default_factory=dict)


class ProviderError(Exception):
    """Raised when a provider call fails after retries."""

    def __init__(
        self, provider: ProviderName, message: str, status_code: int | None = None
    ) -> None:
        super().__init__(f"[{provider.value}] {message}")
        self.provider = provider
        self.status_code = status_code
