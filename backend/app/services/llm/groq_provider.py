"""Groq provider — uses Llama models on Groq's LPU hardware."""

from __future__ import annotations

import time
from typing import cast

from groq import APIStatusError, AsyncGroq, RateLimitError
from groq.types.chat import ChatCompletionMessageParam
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import get_logger
from app.services.llm.types import (
    LLMRequest,
    LLMResponse,
    ProviderError,
    ProviderName,
    TokenUsage,
)

logger = get_logger("llm.groq")


class GroqProvider:
    name: ProviderName = ProviderName.GROQ

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or settings.groq_api_key
        if not key:
            raise ProviderError(self.name, "GROQ_API_KEY is not set")
        self._client = AsyncGroq(api_key=key)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        retrying = AsyncRetrying(
            stop=stop_after_attempt(settings.max_retries),
            wait=wait_exponential(multiplier=settings.initial_retry_delay_seconds, max=30),
            retry=retry_if_exception_type((RateLimitError, APIStatusError)),
            reraise=True,
        )

        started = time.perf_counter()
        try:
            async for attempt in retrying:
                with attempt:
                    response = await self._client.chat.completions.create(
                        model=request.model,
                        messages=cast(
                            list[ChatCompletionMessageParam],
                            [m.model_dump() for m in request.messages],
                        ),
                        temperature=request.temperature,
                        max_tokens=request.max_tokens,
                        seed=request.seed,
                        response_format=request.response_format,  # type: ignore[arg-type]
                    )
        except RateLimitError as exc:
            raise ProviderError(self.name, f"rate limited: {exc}", status_code=429) from exc
        except APIStatusError as exc:
            raise ProviderError(
                self.name, f"api error: {exc}", status_code=exc.status_code
            ) from exc
        except Exception as exc:
            raise ProviderError(self.name, f"unexpected error: {exc}") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        choice = response.choices[0]
        usage = response.usage

        logger.info(
            "llm_call_complete",
            provider=self.name.value,
            model=request.model,
            latency_ms=latency_ms,
            prompt_tokens=getattr(usage, "prompt_tokens", 0),
            completion_tokens=getattr(usage, "completion_tokens", 0),
        )

        return LLMResponse(
            provider=self.name,
            model=request.model,
            content=choice.message.content or "",
            usage=TokenUsage(
                prompt_tokens=getattr(usage, "prompt_tokens", 0),
                completion_tokens=getattr(usage, "completion_tokens", 0),
                total_tokens=getattr(usage, "total_tokens", 0),
            ),
            latency_ms=latency_ms,
            finish_reason=choice.finish_reason,
            raw_response={"id": response.id},
        )
