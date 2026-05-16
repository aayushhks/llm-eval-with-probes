"""Pydantic schemas for golden dataset cases."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.features.code_review.schemas import Category, Severity


class DatasetSubset(StrEnum):
    CLEAN = "clean"
    CLEAR_ISSUES = "clear_issues"
    SYCOPHANCY_BAIT = "sycophancy_bait"
    GROUNDING_BAIT = "grounding_bait"
    SUBTLE_BUGS = "subtle_bugs"


class ExpectedComment(BaseModel):
    """A keyword/category check for one expected issue."""

    must_mention: list[str] = Field(
        description=(
            "The model's review must reference at least one of these terms (case-insensitive)."
        )
    )
    min_severity: Severity = Field(description="Lowest severity that counts as 'caught the issue'.")
    category: Category | None = None


class GoldenCase(BaseModel):
    """One evaluation case."""

    id: str = Field(pattern=r"^[a-z0-9_-]+$")
    subset: DatasetSubset
    description: str = Field(description="One-line human-readable description.")
    diff: str = Field(description="Unified diff to feed the model.")

    should_approve: bool = Field(description="Whether a correct reviewer would approve this diff.")
    expected_issues: list[ExpectedComment] = Field(
        default_factory=list,
        description="Issues a correct reviewer should raise. Empty for clean cases.",
    )
    forbidden_keywords: list[str] = Field(
        default_factory=list,
        description="Substrings that, if present in the model's review, indicate failure "
        "(e.g. praise words in sycophancy_bait cases).",
    )
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
