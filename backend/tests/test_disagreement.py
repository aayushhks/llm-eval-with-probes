"""Tests for the disagreement classifier."""

from __future__ import annotations

import uuid

from app.models.db_models import EvalCase
from app.services.analysis.disagreement import classify_disagreements


def _make_case(
    passed: bool,
    judge_quality: int | None,
    syco: float | None = None,
    uncert: float | None = None,
    ungrnd: float | None = None,
) -> EvalCase:
    return EvalCase(
        id=uuid.uuid4(),
        run_id=uuid.uuid4(),
        case_id="t",
        subset="x",
        passed=passed,
        approve_correct=True,
        issues_caught=0,
        issues_expected=0,
        forbidden_keyword_hits=[],
        latency_ms=0,
        prompt_tokens=0,
        completion_tokens=0,
        judge_quality_score=judge_quality,
        probe_is_sycophantic=syco,
        probe_is_uncertain=uncert,
        probe_is_ungrounded=ungrnd,
    )


def test_det_fail_judge_good() -> None:
    case = _make_case(passed=False, judge_quality=9)
    assert "det_fail_judge_good" in classify_disagreements(case)


def test_probe_says_sycophantic_judge_says_fine() -> None:
    case = _make_case(passed=False, judge_quality=9, syco=0.5)
    flags = classify_disagreements(case)
    assert "probe_says_sycophantic_judge_says_fine" in flags
    assert "det_fail_judge_good" in flags


def test_no_flags_when_everyone_agrees() -> None:
    # clean diff: passes deterministic, high judge, low probe
    case = _make_case(passed=True, judge_quality=9, syco=0.1, uncert=0.1, ungrnd=0.1)
    assert classify_disagreements(case) == []


def test_probe_confirms_failure_via_uncertainty() -> None:
    case = _make_case(passed=False, judge_quality=8, uncert=0.85)
    flags = classify_disagreements(case)
    assert "probe_confirms_failure_via_uncertainty" in flags


def test_missing_probe_scores_skip_probe_flags() -> None:
    case = _make_case(passed=False, judge_quality=9, syco=None, uncert=None)
    flags = classify_disagreements(case)
    assert "det_fail_judge_good" in flags
    assert "probe_says_sycophantic_judge_says_fine" not in flags
