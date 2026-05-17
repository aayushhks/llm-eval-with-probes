"""Tests for the LLM-as-judge service using the mock provider."""

from __future__ import annotations

import json

import pytest

from app.datasets.schemas import (
    DatasetSubset,
    ExpectedComment,
    GoldenCase,
)
from app.features.code_review.schemas import (
    Category,
    ReviewComment,
    ReviewOutput,
    Severity,
)
from app.services.judge.schemas import JudgeOutput
from app.services.judge.service import (
    JudgeParseError,
    _parse_judge_output,
    judge_review,
    load_judge_prompt,
)
from app.services.llm.mock_provider import MockProvider


def _golden() -> GoldenCase:
    return GoldenCase(
        id="t_001",
        subset=DatasetSubset.CLEAR_ISSUES,
        description="x",
        diff="diff --git a/x.py b/x.py\n+password = 'x'\n",
        should_approve=False,
        expected_issues=[
            ExpectedComment(
                must_mention=["password"],
                min_severity=Severity.WARNING,
                category=Category.SECURITY,
            )
        ],
    )


def _review() -> ReviewOutput:
    return ReviewOutput(
        summary="hardcoded creds",
        approves=False,
        comments=[
            ReviewComment(
                line_hint="x.py",
                severity=Severity.WARNING,
                category=Category.SECURITY,
                message="hardcoded password",
            )
        ],
    )


def _valid_judge_payload() -> str:
    return json.dumps(
        {
            "quality_score": 8,
            "caught_real_issues": True,
            "invented_issues": False,
            "appropriately_skeptical": True,
            "reasoning": "Caught the credential issue clearly.",
        }
    )


def test_load_judge_prompt_v1() -> None:
    prompt = load_judge_prompt("v1")
    assert prompt.version == "v1"
    assert "{diff}" in prompt.user_template
    assert "{review_json}" in prompt.user_template


def test_load_judge_prompt_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown judge prompt"):
        load_judge_prompt("v99")


def test_parse_judge_output_valid() -> None:
    out = _parse_judge_output(_valid_judge_payload())
    assert isinstance(out, JudgeOutput)
    assert out.quality_score == 8
    assert out.caught_real_issues is True


def test_parse_judge_output_invalid_json() -> None:
    with pytest.raises(JudgeParseError, match="no JSON object found|not valid JSON"):
        _parse_judge_output("not json at all")


def test_parse_judge_output_schema_violation() -> None:
    bad = json.dumps(
        {
            "quality_score": 99,  # outside 0-10
            "caught_real_issues": True,
            "invented_issues": False,
            "appropriately_skeptical": True,
            "reasoning": "x",
        }
    )
    with pytest.raises(JudgeParseError, match="schema"):
        _parse_judge_output(bad)


class _CannedJsonProvider(MockProvider):
    def __init__(self, payload: str) -> None:
        super().__init__()
        self._payload = payload

    async def complete(self, request):  # type: ignore[override]
        response = await super().complete(request)
        response.content = self._payload
        return response


@pytest.mark.asyncio
async def test_judge_review_happy_path() -> None:
    provider = _CannedJsonProvider(_valid_judge_payload())
    result = await judge_review(
        case=_golden(),
        review=_review(),
        provider=provider,
        model="mock",
    )
    assert result.output is not None
    assert result.output.quality_score == 8
    assert result.parse_error is None


@pytest.mark.asyncio
async def test_judge_review_records_parse_error() -> None:
    provider = _CannedJsonProvider("not json")
    result = await judge_review(
        case=_golden(),
        review=_review(),
        provider=provider,
        model="mock",
    )
    assert result.output is None
    assert result.parse_error is not None
