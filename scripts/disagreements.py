"""Fetch the disagreement view for a run, as JSON. Useful for grepping the
headline cases from the command line.

Usage:
    cd backend && uv run python ../scripts/disagreements.py <run_id>
    cd backend && uv run python ../scripts/disagreements.py <run_id> --raw
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
from app.services.analysis.disagreement import analyze_run, summarize_flags  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", help="UUID of the run to analyze")
    parser.add_argument(
        "--raw", action="store_true", help="dump full JSON of all flagged rows"
    )
    args = parser.parse_args()

    configure_logging("WARNING")

    async with AsyncSessionLocal() as session:
        rows = await analyze_run(session, uuid.UUID(args.run_id))

    flagged = [r for r in rows if r.flags]
    if args.raw:
        print(json.dumps([r.to_dict() for r in flagged], indent=2, default=str))
    else:
        print(f"\nRun: {args.run_id}")
        print(f"Cases: {len(rows)}, flagged: {len(flagged)}\n")
        for r in flagged:
            print(f"  {r.case_id} ({r.subset})")
            print(f"    det: {'PASS' if r.deterministic_passed else 'FAIL'}")
            print(f"    judge: {r.judge_quality}/10")
            print(
                f"    probes: syco={r.probe_sycophantic:.2f}, "
                f"uncert={r.probe_uncertain:.2f}, "
                f"ungrnd={r.probe_ungrounded:.2f}, "
                f"refuse={r.probe_refusing:.2f}"
            )
            for f in r.flags:
                print(f"    > {f}")
            print()

        print("Flag totals:")
        print(json.dumps(summarize_flags(rows), indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))