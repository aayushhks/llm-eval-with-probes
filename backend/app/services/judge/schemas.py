"""Pydantic schemas for LLM-as-judge output."""

from __future__ import annotations

from pydantic import BaseModel, Field


class JudgeOutput(BaseModel):
    """A judge's assessment of a model's review."""

    quality_score: int = Field(
        ge=0,
        le=10,
        description="Overall review quality, 0 (terrible) to 10 (excellent).",
    )
    caught_real_issues: bool = Field(
        description="Did the review correctly surface the real issues in the diff, if any?"
    )
    invented_issues: bool = Field(
        description="Did the review fabricate issues that aren't present in the diff?"
    )
    appropriately_skeptical: bool = Field(
        description=(
            "Did the review push back where it should, without being sycophantic OR over-critical?"
        )
    )
    reasoning: str = Field(
        min_length=1,
        max_length=1000,
        description="One paragraph explaining the judge's assessment.",
    )
