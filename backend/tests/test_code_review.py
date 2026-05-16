"""Tests for the code review feature using the mock provider."""

from __future__ import annotations

import json

import pytest

from app.features.code_review.parser import ReviewParseError, parse_review_output
from app.features.code_review.prompt_loader import list_versions, load_prompt
from app.features.code_review.schemas import Category, ReviewOutput, Severity
from app.features.code_review.service import review_code_diff
from app.services.llm.mock_provider import MockProvider


# ---------- prompt loader ----------


def test_list_versions_contains_v1_and_v2() -> None:
    versions = list_versions()
    assert "v1" in versions
    assert "v2" in versions


def test_load_prompt_returns_typed_prompt() -> None:
    prompt = load_prompt("v1")
    assert prompt.version == "v1"
    assert "{diff}" in prompt.user_template
    assert prompt.system  # non-empty


def test_load_prompt_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown prompt version"):
        load_prompt("v99")


def test_format_user_substitutes_diff() -> None:
    prompt = load_prompt("v1")
    rendered = prompt.format_user("the-diff-here")
    assert "the-diff-here" in rendered


# ---------- parser ----------


def _valid_review_json() -> str:
    return json.dumps(
        {
            "summary": "Adds a hardcoded password.",
            "approves": False,
            "comments": [
                {
                    "line_hint": "auth.py admin_password",
                    "severity": "blocker",
                    "category": "security",
                    "message": "Hardcoded credentials must be moved to a secrets store.",
                }
            ],
        }
    )


def test_parser_accepts_clean_json() -> None:
    result = parse_review_output(_valid_review_json())
    assert isinstance(result, ReviewOutput)
    assert result.approves is False
    assert len(result.comments) == 1
    assert result.comments[0].severity == Severity.BLOCKER
    assert result.comments[0].category == Category.SECURITY


def test_parser_strips_code_fences() -> None:
    wrapped = f"```json\n{_valid_review_json()}\n```"
    result = parse_review_output(wrapped)
    assert result.approves is False


def test_parser_handles_prose_around_json() -> None:
    noisy = f"Sure! Here is the review:\n\n{_valid_review_json()}\n\nLet me know."
    result = parse_review_output(noisy)
    assert len(result.comments) == 1


def test_parser_rejects_non_json() -> None:
    with pytest.raises(ReviewParseError, match="no JSON object found"):
        parse_review_output("just some prose")


def test_parser_rejects_schema_violation() -> None:
    bad = json.dumps(
        {
            "summary": "x",
            "approves": True,
            "comments": [
                {
                    "line_hint": "y",
                    "severity": "catastrophic",  # not a valid Severity
                    "category": "security",
                    "message": "z",
                }
            ],
        }
    )
    with pytest.raises(ReviewParseError, match="schema validation"):
        parse_review_output(bad)


# ---------- end-to-end with mock provider ----------


class _CannedJsonProvider(MockProvider):
    """A mock that returns a fixed JSON review string."""

    def __init__(self, payload: str) -> None:
        super().__init__(canned_response=payload)

    async def complete(self, request):  # type: ignore[override]
        # Reuse parent but force content to be the payload only (not the echo formatting)
        response = await super().complete(request)
        response.content = self._canned_response
        return response


@pytest.mark.asyncio
async def test_review_code_diff_returns_parsed_output() -> None:
    provider = _CannedJsonProvider(_valid_review_json())
    result = await review_code_diff(
        diff="diff --git a/auth.py b/auth.py\n+admin_password = 'x'",
        provider=provider,
        model="mock",
        prompt_version="v1",
    )
    assert result.parse_error is None
    assert result.output.approves is False
    assert result.prompt_version == "v1"


@pytest.mark.asyncio
async def test_review_code_diff_records_parse_error() -> None:
    provider = _CannedJsonProvider("not valid json at all")
    result = await review_code_diff(
        diff="diff",
        provider=provider,
        model="mock",
        prompt_version="v1",
    )
    assert result.parse_error is not None
    assert result.output.summary == "<parse error>"