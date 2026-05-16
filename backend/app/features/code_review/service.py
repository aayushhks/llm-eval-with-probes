"""Public entry point: send a diff, get back a validated ReviewOutput."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logging import get_logger
from app.features.code_review.parser import ReviewParseError, parse_review_output
from app.features.code_review.prompt_loader import load_prompt
from app.features.code_review.schemas import ReviewOutput
from app.services.llm.base import LLMProvider
from app.services.llm.types import LLMRequest, LLMResponse, Message

logger = get_logger("feature.code_review")


@dataclass
class ReviewResult:
    """Bundle the parsed output with the raw LLM response for traceability."""

    output: ReviewOutput
    raw_response: LLMResponse
    prompt_version: str
    parse_error: str | None = None


async def review_code_diff(
    diff: str,
    provider: LLMProvider,
    model: str,
    prompt_version: str = "v1",
    temperature: float = 0.0,
    max_tokens: int = 1500,
) -> ReviewResult:
    """Run the code review feature on a diff."""
    prompt = load_prompt(prompt_version)

    request = LLMRequest(
        messages=[
            Message(role="system", content=prompt.system),
            Message(role="user", content=prompt.format_user(diff)),
        ],
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )

    response = await provider.complete(request)

    try:
        parsed = parse_review_output(response.content)
        return ReviewResult(
            output=parsed,
            raw_response=response,
            prompt_version=prompt_version,
        )
    except ReviewParseError as exc:
        logger.warning(
            "review_parse_failed",
            error=str(exc),
            prompt_version=prompt_version,
            content_preview=response.content[:200],
        )
        # Return a failure shell rather than raising — eval runner will record it
        empty = ReviewOutput(
            summary="<parse error>",
            approves=False,
            comments=[],
        )
        return ReviewResult(
            output=empty,
            raw_response=response,
            prompt_version=prompt_version,
            parse_error=str(exc),
        )
