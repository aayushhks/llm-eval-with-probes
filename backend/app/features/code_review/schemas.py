"""Pydantic schemas for the code review feature."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Severity(StrEnum):
    NIT = "nit"
    SUGGESTION = "suggestion"
    WARNING = "warning"
    BLOCKER = "blocker"


class Category(StrEnum):
    SECURITY = "security"
    PERFORMANCE = "performance"
    CORRECTNESS = "correctness"
    READABILITY = "readability"
    STYLE = "style"
    TESTING = "testing"
    OTHER = "other"


class ReviewComment(BaseModel):
    """A single inline review comment."""

    line_hint: str = Field(
        description="Short hint about which line(s) this applies to. "
        "Examples: 'line 42', 'auth.py lines 10-15', 'the new function'."
    )
    severity: Severity
    category: Category
    message: str = Field(min_length=1, max_length=600)

    @field_validator("message")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()


class ReviewOutput(BaseModel):
    """Top-level model response after parsing."""

    summary: str = Field(
        description="One-sentence overall verdict on the diff.",
        min_length=1,
        max_length=300,
    )
    approves: bool = Field(
        description="Does the reviewer approve this diff as-is? "
        "(Independent of comments; a model can comment AND approve.)"
    )
    comments: list[ReviewComment] = Field(default_factory=list)
