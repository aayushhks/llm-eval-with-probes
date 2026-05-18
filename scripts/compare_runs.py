"""Compare two eval runs and print regressions/improvements.

Usage:
    cd backend && uv run python ../scripts/compare_runs.py <run_a> <run_b>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.services.analysis.regression import diff_runs, summarize_diff  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_a", help="baseline run id")
    parser.add_argument("run_b", help="candidate run id")
    parser.add_argument("--json", action="store_true", help="emit full JSON")
    args = parser.parse_args()

    configure_logging("WARNING")

    async with AsyncSessionLocal() as session:
        diffs = await diff_runs(
            session, uuid.UUID(args.run_a), uuid.UUID(args.run_b)
        )
    summary = summarize_diff(diffs)

    if args.json:
        print(json.dumps([d.to_dict() for d in diffs], indent=2, default=str))
        return 0

    print(f"\nCompared {len(diffs)} cases\n")
    print(json.dumps(summary, indent=2))
    print()

    regressions = [d for d in diffs if d.overall_change == "regression"]
    if regressions:
        print(f"Regressions ({len(regressions)}):")
        for d in regressions:
            print(f"  {d.case_id} ({d.subset})")
            if d.deterministic_change == "regression":
                print("    det: PASS → FAIL")
            if d.judge_change == "regression":
                print(f"    judge: {d.judge_a} → {d.judge_b} (Δ={d.judge_delta})")
            for name, c in d.probe_changes.items():
                if c == "regression":
                    delta = d.probe_deltas.get(name)
                    print(f"    probe {name}: Δ=+{delta:.2f}")
            print()

    return 0 if summary["regression"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))