"""Run a full eval against Postgres. Persists results for later comparison.

Usage:
    cd backend && uv run python ../scripts/run_eval.py --prompt v1
    cd backend && uv run python ../scripts/run_eval.py --prompt v2 --subset clean
    cd backend && uv run python ../scripts/run_eval.py --prompt v1 --notes "first full run"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.config import settings  # noqa: E402
from app.core.database import AsyncSessionLocal  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.datasets.schemas import DatasetSubset  # noqa: E402
from app.services.eval.runner import EvalRunConfig, run_eval  # noqa: E402
from app.services.llm.registry import get_provider  # noqa: E402
from app.services.llm.types import ProviderName  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default="v1")
    parser.add_argument("--model", default=settings.default_subject_model)
    parser.add_argument(
        "--provider",
        default=ProviderName.GROQ.value,
        choices=[p.value for p in ProviderName],
    )
    parser.add_argument(
        "--subset", choices=[s.value for s in DatasetSubset], default=None
    )
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--rpm", type=int, default=25)
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    configure_logging("WARNING")

    config = EvalRunConfig(
        prompt_version=args.prompt,
        model=args.model,
        provider_name=ProviderName(args.provider),
        subset=args.subset,
        concurrency=args.concurrency,
        requests_per_minute=args.rpm,
        notes=args.notes,
    )

    provider = get_provider(config.provider_name)

    async with AsyncSessionLocal() as session:
        run = await run_eval(config, provider, session)

    print(f"\nRun id: {run.id}")
    print(f"Status: {run.status.value}")
    print(f"Duration: {(run.finished_at - run.started_at).total_seconds():.1f}s")
    print(json.dumps(run.summary_json, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))