"""Run counterbalanced prompt pairs and record provenance. Requires DB + provider credentials.
Dry run by default. --execute makes real API calls and can incur provider charges.
"""

from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def plan(rounds):
    if rounds < 3:
        raise ValueError("Use at least three paired rounds")
    return [["v1", "v2"] if i % 2 == 0 else ["v2", "v1"] for i in range(rounds)]


async def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--dataset", type=Path, default=ROOT / "datasets/code_review/golden_v1.jsonl")
    p.add_argument("--model", default="llama-3.1-8b-instant")
    p.add_argument("--judge-model", default="llama-3.3-70b-versatile")
    p.add_argument("--rpm", type=int, default=20)
    p.add_argument("--no-probes", action="store_true")
    p.add_argument("--execute", action="store_true")
    p.add_argument("--output", type=Path, default=ROOT / "docs/results/repeated-eval.json")
    args = p.parse_args()
    order = plan(args.rounds)
    from app.datasets.loader import load_dataset

    cases = load_dataset(args.dataset)
    report = {
        "schema_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "dataset_sha256": hashlib.sha256(args.dataset.read_bytes()).hexdigest(),
        "case_ids": [c.id for c in cases],
        "git_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "working_tree_dirty": bool(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip()
        ),
        "subject_temperature": 0.0,
        "subject_max_tokens": 1500,
        "prompt_hashes": {
            v: hashlib.sha256(
                (ROOT / f"backend/app/features/code_review/prompts/{v}.yaml").read_bytes()
            ).hexdigest()
            for v in ("v1", "v2")
        },
        "model": args.model,
        "judge_model": args.judge_model,
        "probe_requested": not args.no_probes,
        "order": order,
        "rounds": [],
        "status": "planned",
    }
    if not args.execute:
        print(json.dumps(report, indent=2))
        return
    from app.core.config import settings
    from app.core.database import AsyncSessionLocal
    from app.services.eval.runner import EvalRunConfig, run_eval
    from app.services.eval.repeats import summarize_pairs
    from app.services.llm.registry import get_provider
    from app.services.llm.types import ProviderName
    from app.services.probes.scorer import probes_available

    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is required for real repeated experiments")
    if not args.no_probes and not probes_available():
        raise RuntimeError(
            "Train probes first, or explicitly use --no-probes for a rules/judge-only study"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError("Choose a new output path; previous experiment records are preserved")

    def checkpoint():
        args.output.write_text(json.dumps(report, indent=2) + "\n")

    report["status"] = "running"
    checkpoint()
    try:
        for i, prompts in enumerate(order):
            pair = {"round": i + 1}
            for prompt in prompts:
                config = EvalRunConfig(
                    prompt_version=prompt,
                    model=args.model,
                    provider_name=ProviderName.GROQ,
                    dataset_path=args.dataset,
                    concurrency=1,
                    requests_per_minute=args.rpm,
                    judge_model=args.judge_model,
                    probes_enabled=not args.no_probes,
                    notes=f"paired repeat {i + 1}/{args.rounds}; {report['dataset_sha256']}",
                )
                async with AsyncSessionLocal() as session:
                    run = await run_eval(config, get_provider(ProviderName.GROQ), session)
                pair["a" if prompt == "v1" else "b"] = {
                    "id": str(run.id),
                    "prompt": prompt,
                    **run.summary_json,
                }
                report["in_progress_pair"] = pair
                checkpoint()
            report["rounds"].append(pair)
            report.pop("in_progress_pair", None)
            report["summary"] = summarize_pairs(report["rounds"])
            checkpoint()
        report["status"] = "completed"
    except Exception:
        report["status"] = "failed"
        checkpoint()
        raise
    checkpoint()
    print(f"Saved real repeat results to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
