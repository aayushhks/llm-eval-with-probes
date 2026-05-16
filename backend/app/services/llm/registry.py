"""Get the right provider instance by name."""

from __future__ import annotations

from app.services.llm.base import LLMProvider
from app.services.llm.gemini_provider import GeminiProvider
from app.services.llm.groq_provider import GroqProvider
from app.services.llm.mock_provider import MockProvider
from app.services.llm.types import ProviderName


def get_provider(name: ProviderName) -> LLMProvider:
    if name == ProviderName.GROQ:
        return GroqProvider()
    if name == ProviderName.GEMINI:
        return GeminiProvider()
    if name == ProviderName.MOCK:
        return MockProvider()
    raise ValueError(f"Unknown provider: {name}")
