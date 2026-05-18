"""Google Gemini provider via google-genai SDK."""

from __future__ import annotations

import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types
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

logger = get_logger("llm.gemini")


class GeminiProvider:
    name: ProviderName = ProviderName.GEMINI

    def __init__(self, api_key: str | None = None) -> None:
        key = api_key or settings.gemini_api_key
        if not key:
            raise ProviderError(self.name, "GEMINI_API_KEY is not set")
        self._client = genai.Client(api_key=key)

    async def complete(self, request: LLMRequest) -> LLMResponse:
        system_text, contents = self._convert_messages(request)

        config = genai_types.GenerateContentConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
            system_instruction=system_text or None,
        )

        retrying = AsyncRetrying(
            stop=stop_after_attempt(settings.max_retries),
            wait=wait_exponential(multiplier=settings.initial_retry_delay_seconds, max=30),
            retry=retry_if_exception_type(genai_errors.APIError),
            reraise=True,
        )

        started = time.perf_counter()
        try:
            async for attempt in retrying:
                with attempt:
                    response = await self._client.aio.models.generate_content(
                        model=request.model,
                        contents=contents,  # type: ignore[arg-type]
                        config=config,
                    )
        except genai_errors.APIError as exc:
            raise ProviderError(
                self.name, f"api error: {exc}", status_code=getattr(exc, "code", None)
            ) from exc
        except Exception as exc:
            raise ProviderError(self.name, f"unexpected error: {exc}") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        text = response.text or ""
        usage_meta = response.usage_metadata

        prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
        completion_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0

        logger.info(
            "llm_call_complete",
            provider=self.name.value,
            model=request.model,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

        return LLMResponse(
            provider=self.name,
            model=request.model,
            content=text,
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            latency_ms=latency_ms,
            finish_reason=str(response.candidates[0].finish_reason)
            if response.candidates
            else None,
            raw_response={},
        )

    @staticmethod
    def _convert_messages(request: LLMRequest) -> tuple[str, list[genai_types.Content]]:
        """Gemini handles system prompts as a separate field, not a message."""
        system_parts: list[str] = []
        contents: list[genai_types.Content] = []
        for msg in request.messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            else:
                role = "user" if msg.role == "user" else "model"
                contents.append(
                    genai_types.Content(
                        role=role,
                        parts=[genai_types.Part(text=msg.content)],
                    )
                )
        return "\n\n".join(system_parts), contents
