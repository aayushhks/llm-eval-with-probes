"""Run a slice of the golden dataset against the feature. Smoke test for the runner.

Full eval pipeline (DB, traces, regression) comes in M4. This is the fast feedback loop.

Usage:
    cd backend && uv run python ../scripts/run_eval_slice.py --subset sycophancy_bait
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.config import settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.datasets.loader import filter_subset, load_dataset  # noqa: E402
from app.datasets.schemas import DatasetSubset  # noqa: E402
from app.datasets.scorer import score_case  # noqa: E402
from app.features.code_review.service import review_code_diff  # noqa: E402
from app.services.llm.registry import get_provider  # noqa: E402
from app.services.llm.types import ProviderName  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subset", choices=[s.value for s in DatasetSubset], default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--prompt", default="v1")
    parser.add_argument("--model", default=settings.default_subject_model)
    parser.add_argument("--provider", default=ProviderName.GROQ.value)
    args = parser.parse_args()

    configure_logging("WARNING")
    cases = load_dataset()
    if args.subset:
        cases = filter_subset(cases, DatasetSubset(args.subset))
    if args.limit:
        cases = cases[: args.limit]

    print(f"Running {len(cases)} cases with prompt={args.prompt} model={args.model}")

    provider = get_provider(ProviderName(args.provider))

    passed = 0
    by_subset: dict[str, dict[str, int]] = {}
    for case in cases:
        result = await review_code_diff(
            diff=case.diff,
            provider=provider,
            model=args.model,
            prompt_version=args.prompt,
        )
        score = score_case(case, result.output, result.parse_error)
        marker = "✓" if score.passed else "✗"
        notes = []
        if not score.approve_correct:
            notes.append(f"approves={result.output.approves} expected={case.should_approve}")
        if score.issues_caught < score.issues_expected:
            notes.append(f"caught {score.issues_caught}/{score.issues_expected}")
        if score.forbidden_keyword_hits:
            notes.append(f"forbidden: {score.forbidden_keyword_hits}")
        if score.parse_error:
            notes.append(f"parse_error: {score.parse_error}")
        suffix = "  " + " | ".join(notes) if notes else ""
        print(f"  {marker} {case.id:<35} [{case.subset.value:<16}]{suffix}")
        if score.passed:
            passed += 1
        bucket = by_subset.setdefault(case.subset.value, {"passed": 0, "total": 0})
        bucket["total"] += 1
        if score.passed:
            bucket["passed"] += 1

    print(f"\nOverall: {passed}/{len(cases)} passed")
    print("Per subset:")
    for subset, b in sorted(by_subset.items()):
        print(f"  {subset:<16} {b['passed']}/{b['total']}")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))