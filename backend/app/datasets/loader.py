"""Load and validate the golden dataset from JSONL."""

from __future__ import annotations

import json
from pathlib import Path

from app.datasets.schemas import DatasetSubset, GoldenCase

DEFAULT_DATASET_PATH = (
    Path(__file__).resolve().parents[3] / "datasets" / "code_review" / "golden_v1.jsonl"
)


def load_dataset(path: Path | None = None) -> list[GoldenCase]:
    """Load all cases from a JSONL file. Validates every row."""
    target = path or DEFAULT_DATASET_PATH
    if not target.exists():
        raise FileNotFoundError(f"Dataset not found at {target}")

    cases: list[GoldenCase] = []
    seen_ids: set[str] = set()
    with target.open() as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Line {i}: invalid JSON: {exc}") from exc
            case = GoldenCase.model_validate(data)
            if case.id in seen_ids:
                raise ValueError(f"Duplicate case id: {case.id}")
            seen_ids.add(case.id)
            cases.append(case)
    return cases


def filter_subset(cases: list[GoldenCase], subset: DatasetSubset) -> list[GoldenCase]:
    return [c for c in cases if c.subset == subset]


def subset_counts(cases: list[GoldenCase]) -> dict[str, int]:
    counts: dict[str, int] = {s.value: 0 for s in DatasetSubset}
    for c in cases:
        counts[c.subset.value] += 1
    return counts
