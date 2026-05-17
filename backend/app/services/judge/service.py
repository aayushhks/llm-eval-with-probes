"""LLM-as-judge: evaluates a code review for quality."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from app.core.logging import get_logger
from app.datasets.schemas import GoldenCase
from app.features.code_review.parser import ReviewParseError, _extract_json_candidate
from app.features.code_review.schemas import ReviewOutput
from app.services.judge.schemas import JudgeOutput
from app.services.llm.base import LLMProvider
from app.services.llm.types import LLMRequest, LLMResponse, Message

logger = get_logger("service.judge")

PROMPTS_DIR = Path(__file__).parent / "prompts"


class JudgePrompt(BaseModel):
    version: str
    description: str = ""
    system: str
    user_template: str = Field(
        description="Format string with {diff}, {review_json}, {expected_issues_json} placeholders."
    )

    def format_user(self, diff: str, review: ReviewOutput, expected_issues_json: str) -> str:
        return self.user_template.format(
            diff=diff,
            review_json=json.dumps(review.model_dump(mode="json"), indent=2),
            expected_issues_json=expected_issues_json,
        )


@lru_cache(maxsize=8)
def load_judge_prompt(version: str = "v1") -> JudgePrompt:
    path = PROMPTS_DIR / f"{version}.yaml"
    if not path.exists():
        raise ValueError(f"Unknown judge prompt version: {version!r}")
    with path.open() as f:
        data = yaml.safe_load(f)
    return JudgePrompt.model_validate(data)


@dataclass
class JudgeResult:
    output: JudgeOutput | None
    raw_response: LLMResponse
    prompt_version: str
    parse_error: str | None = None


class JudgeParseError(Exception):
    """Raised when judge output can't be parsed."""


def _parse_judge_output(raw: str) -> JudgeOutput:
    try:
        candidate = _extract_json_candidate(raw)
    except ReviewParseError as exc:
        raise JudgeParseError(f"no JSON object found in output: {exc}") from exc
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise JudgeParseError(f"judge output not valid JSON: {exc.msg}") from exc
    try:
        return JudgeOutput.model_validate(data)
    except ValidationError as exc:
        raise JudgeParseError(f"judge output failed schema: {exc}") from exc


async def judge_review(
    case: GoldenCase,
    review: ReviewOutput,
    provider: LLMProvider,
    model: str,
    prompt_version: str = "v1",
    max_tokens: int = 800,
) -> JudgeResult:
    """Ask the judge LLM whether the review is any good."""
    prompt = load_judge_prompt(prompt_version)
    expected_issues_json = json.dumps(
        [e.model_dump(mode="json") for e in case.expected_issues], indent=2
    )

    request = LLMRequest(
        messages=[
            Message(role="system", content=prompt.system),
            Message(
                role="user",
                content=prompt.format_user(case.diff, review, expected_issues_json),
            ),
        ],
        model=model,
        temperature=0.0,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )

    response = await provider.complete(request)

    try:
        parsed = _parse_judge_output(response.content)
        return JudgeResult(output=parsed, raw_response=response, prompt_version=prompt_version)
    except JudgeParseError as exc:
        logger.warning(
            "judge_parse_failed",
            error=str(exc),
            case_id=case.id,
            content_preview=response.content[:200],
        )
        return JudgeResult(
            output=None,
            raw_response=response,
            prompt_version=prompt_version,
            parse_error=str(exc),
        )
