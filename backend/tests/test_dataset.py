"""Tests for the golden dataset loader and scorer."""

from __future__ import annotations

import json

import pytest
from app.datasets.loader import filter_subset, load_dataset, subset_counts

from app.datasets.schemas import DatasetSubset, ExpectedComment, GoldenCase
from app.datasets.scorer import score_case
from app.features.code_review.schemas import (
    Category,
    ReviewComment,
    ReviewOutput,
    Severity,
)

# ---------- loader ----------


def test_load_dataset_loads_and_validates() -> None:
    cases = load_dataset()
    assert len(cases) >= 20
    assert all(isinstance(c, GoldenCase) for c in cases)


def test_load_dataset_has_all_subsets() -> None:
    cases = load_dataset()
    counts = subset_counts(cases)
    for subset in DatasetSubset:
        assert counts[subset.value] > 0, f"empty subset: {subset}"


def test_load_dataset_ids_unique(tmp_path) -> None:
    # build a synthetic file with a duplicate id
    path = tmp_path / "dup.jsonl"
    case = {
        "id": "dup_a",
        "subset": "clean",
        "description": "x",
        "diff": "diff",
        "should_approve": True,
        "expected_issues": [],
        "forbidden_keywords": [],
        "tags": [],
        "notes": "",
    }
    with path.open("w") as f:
        f.write(json.dumps(case) + "\n")
        f.write(json.dumps(case) + "\n")
    with pytest.raises(ValueError, match="Duplicate"):
        load_dataset(path)


def test_filter_subset() -> None:
    cases = load_dataset()
    clean = filter_subset(cases, DatasetSubset.CLEAN)
    assert all(c.subset == DatasetSubset.CLEAN for c in clean)


# ---------- scorer ----------


def _golden_with_one_issue() -> GoldenCase:
    return GoldenCase(
        id="t_001",
        subset=DatasetSubset.CLEAR_ISSUES,
        description="hardcoded creds",
        diff="diff",
        should_approve=False,
        expected_issues=[
            ExpectedComment(
                must_mention=["hardcoded", "password"],
                min_severity=Severity.WARNING,
                category=Category.SECURITY,
            )
        ],
        forbidden_keywords=["looks good"],
    )


def _good_review() -> ReviewOutput:
    return ReviewOutput(
        summary="Hardcoded admin password is a security risk.",
        approves=False,
        comments=[
            ReviewComment(
                line_hint="auth.py admin",
                severity=Severity.BLOCKER,
                category=Category.SECURITY,
                message="The hardcoded password must be moved to env vars.",
            )
        ],
    )


def test_score_case_full_pass() -> None:
    score = score_case(_golden_with_one_issue(), _good_review())
    assert score.passed
    assert score.approve_correct
    assert score.issues_caught == 1
    assert score.issue_recall == 1.0


def test_score_case_missed_issue() -> None:
    review = ReviewOutput(summary="seems fine", approves=False, comments=[])
    score = score_case(_golden_with_one_issue(), review)
    assert not score.passed
    assert score.issues_caught == 0
    assert score.approve_correct  # approves=False matches should_approve=False


def test_score_case_wrong_approval() -> None:
    review = ReviewOutput(summary="lgtm", approves=True, comments=[])
    score = score_case(_golden_with_one_issue(), review)
    assert not score.passed
    assert not score.approve_correct


def test_score_case_forbidden_keyword_fails() -> None:
    review = ReviewOutput(
        summary="Looks good, but the hardcoded password should be moved.",
        approves=False,
        comments=[
            ReviewComment(
                line_hint="auth.py",
                severity=Severity.WARNING,
                category=Category.SECURITY,
                message="The hardcoded password is a problem.",
            )
        ],
    )
    score = score_case(_golden_with_one_issue(), review)
    assert "looks good" in score.forbidden_keyword_hits
    assert not score.passed


def test_score_case_parse_error_fails() -> None:
    score = score_case(
        _golden_with_one_issue(),
        ReviewOutput(summary="x", approves=False, comments=[]),
        parse_error="bad json",
    )
    assert not score.passed
    assert score.parse_error == "bad json"


def test_score_case_clean_dataset_no_expected_issues() -> None:
    case = GoldenCase(
        id="clean_x",
        subset=DatasetSubset.CLEAN,
        description="x",
        diff="diff",
        should_approve=True,
        expected_issues=[],
    )
    review = ReviewOutput(summary="lgtm", approves=True, comments=[])
    score = score_case(case, review)
    assert score.passed
    assert score.issue_recall == 1.0
