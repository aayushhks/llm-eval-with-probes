"""Parse model output into a validated ReviewOutput. Handles common failure modes."""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.features.code_review.schemas import ReviewOutput


class ReviewParseError(Exception):
    """Raised when model output can't be parsed into a ReviewOutput."""


# Match ```json ... ``` or ``` ... ``` code fences
_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def parse_review_output(raw: str) -> ReviewOutput:
    """
    Parse raw model output into a ReviewOutput.

    Tolerates a few common failure modes:
    - Model wrapped the JSON in ```json ... ``` fences
    - Model added prose before/after the JSON
    - Trailing commas (we don't try to fix these; we surface as parse error)
    """
    candidate = _extract_json_candidate(raw)

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ReviewParseError(f"output was not valid JSON: {exc.msg} at pos {exc.pos}") from exc

    try:
        return ReviewOutput.model_validate(data)
    except ValidationError as exc:
        raise ReviewParseError(f"output failed schema validation: {exc}") from exc


def _extract_json_candidate(raw: str) -> str:
    """Strip fences and grab the outermost JSON object."""
    stripped = raw.strip()

    # If wrapped in code fences, take inner content
    fence_match = _FENCE_PATTERN.search(stripped)
    if fence_match:
        stripped = fence_match.group(1).strip()

    # Find outermost {...}
    first = stripped.find("{")
    last = stripped.rfind("}")
    if first == -1 or last == -1 or last < first:
        raise ReviewParseError("no JSON object found in output")
    return stripped[first : last + 1]
