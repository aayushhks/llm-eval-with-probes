"""Mock provider — deterministic responses, no network. For tests and offline dev."""

from __future__ import annotations

import time

from app.services.llm.types import (
    LLMRequest,
    LLMResponse,
    ProviderName,
    TokenUsage,
)


class MockProvider:
    name: ProviderName = ProviderName.MOCK

    def __init__(self, canned_response: str = "mock response") -> None:
        self._canned_response = canned_response

    async def complete(self, request: LLMRequest) -> LLMResponse:
        started = time.perf_counter()
        # Simulate small latency
        await _no_op()
        latency_ms = int((time.perf_counter() - started) * 1000)

        # Echo the last user message for traceability
        last_user_message = next(
            (m.content for m in reversed(request.messages) if m.role == "user"),
            "",
        )
        content = f"{self._canned_response} | last_user_message={last_user_message[:80]}"

        return LLMResponse(
            provider=self.name,
            model=request.model,
            content=content,
            usage=TokenUsage(
                prompt_tokens=len(" ".join(m.content for m in request.messages).split()),
                completion_tokens=len(content.split()),
                total_tokens=0,
            ),
            latency_ms=latency_ms,
            finish_reason="stop",
            raw_response={"mocked": True},
        )


async def _no_op() -> None:
    return None
