"""Analyze a completed eval run: disagreement table + plots.

Usage:
    cd backend && uv run python ../scripts/analyze_run.py <run_id>
    cd backend && uv run python ../scripts/analyze_run.py <run_id_v1> --compare <run_id_v2>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.services.analysis.disagreement import analyze_run, summarize_flags  # noqa: E402
from app.services.analysis.plots import (  # noqa: E402
    per_subset_scorer_comparison,
    probe_vs_judge_scatter,
    scorer_agreement_heatmap,
)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id", help="UUID of the run to analyze")
    parser.add_argument("--compare", help="optional v2 run id for side-by-side")
    repo_root = Path(__file__).resolve().parents[1]
    parser.add_argument(
        "--out",
        default=str(repo_root / "docs" / "figures"),
        help="output directory for plots",
    )
    args = parser.parse_args()

    configure_logging("WARNING")
    out_dir = Path(args.out)

    async with AsyncSessionLocal() as session:
        rows = await analyze_run(session, uuid.UUID(args.run_id))

        # Per-case disagreement table (printed to stdout, useful for resume)
        print(f"\nRun: {args.run_id}")
        print(f"Cases analyzed: {len(rows)}")
        print("\nPer-case disagreement flags:")
        for r in rows:
            if r.flags:
                print(f"  {r.case_id} ({r.subset}): {', '.join(r.flags)}")

        flag_counts = summarize_flags(rows)
        print("\nFlag totals:")
        print(json.dumps(flag_counts, indent=2))

        # Plots
        scatter = probe_vs_judge_scatter(rows, out_dir)
        print(f"\nSaved: {scatter.png}")

        heatmap = scorer_agreement_heatmap(rows, out_dir)
        print(f"Saved: {heatmap.png}")

        if args.compare:
            rows_v2 = await analyze_run(session, uuid.UUID(args.compare))
            comparison = per_subset_scorer_comparison(rows, rows_v2, out_dir)
            print(f"Saved: {comparison.png}")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))