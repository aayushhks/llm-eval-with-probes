"""Manual smoke test for all three providers. Run from backend/ with uv."""

from __future__ import annotations

import asyncio
import os
import sys

# Ensure backend/ is importable when run as a script
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.config import settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.services.llm.registry import get_provider  # noqa: E402
from app.services.llm.types import LLMRequest, Message, ProviderName  # noqa: E402


PROMPT = [
    Message(
        role="system",
        content="You review code diffs. Reply with exactly one short sentence.",
    ),
    Message(
        role="user",
        content="A diff adds `password = 'admin'` as a hardcoded credential. "
        "Is this a security concern?",
    ),
]


async def run_one(provider_name: ProviderName, model: str) -> None:
    print(f"\n=== {provider_name.value} :: {model} ===")
    try:
        provider = get_provider(provider_name)
    except Exception as exc:
        print(f"  skipped ({exc})")
        return

    request = LLMRequest(messages=PROMPT, model=model, temperature=0.0, max_tokens=120)
    try:
        response = await provider.complete(request)
    except Exception as exc:
        print(f"  error: {exc}")
        return

    print(f"  content: {response.content.strip()}")
    print(
        f"  tokens: prompt={response.usage.prompt_tokens} "
        f"completion={response.usage.completion_tokens}"
    )
    print(f"  latency: {response.latency_ms}ms")


async def main() -> None:
    configure_logging("WARNING")  # quiet structlog so prints stand out

    await run_one(ProviderName.MOCK, "mock-model")

    if settings.groq_api_key:
        await run_one(ProviderName.GROQ, settings.default_subject_model)
        await run_one(ProviderName.GROQ, settings.default_judge_model)
    else:
        print("\n=== groq :: skipped (no GROQ_API_KEY) ===")

    if settings.gemini_api_key:
        await run_one(ProviderName.GEMINI, settings.default_gemini_model)
    else:
        print("\n=== gemini :: skipped (no GEMINI_API_KEY) ===")


if __name__ == "__main__":
    asyncio.run(main())