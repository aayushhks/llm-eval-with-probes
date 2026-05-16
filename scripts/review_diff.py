"""Run the code review feature against a diff file. Usage:

    cd backend && uv run python ../scripts/review_diff.py \\
        ../datasets/code_review/sample_diffs/01_hardcoded_password.diff
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.core.config import settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.features.code_review.prompt_loader import list_versions  # noqa: E402
from app.features.code_review.service import review_code_diff  # noqa: E402
from app.services.llm.registry import get_provider  # noqa: E402
from app.services.llm.types import ProviderName  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("diff_path", type=Path)
    parser.add_argument(
        "--provider", default=ProviderName.GROQ.value, choices=[p.value for p in ProviderName]
    )
    parser.add_argument("--model", default=settings.default_subject_model)
    parser.add_argument("--prompt", default="v1", choices=list_versions())
    args = parser.parse_args()

    configure_logging("WARNING")

    diff_text = args.diff_path.read_text()
    provider = get_provider(ProviderName(args.provider))

    result = await review_code_diff(
        diff=diff_text,
        provider=provider,
        model=args.model,
        prompt_version=args.prompt,
    )

    print(f"=== {args.diff_path.name} :: {args.provider}/{args.model} :: prompt={args.prompt} ===")
    if result.parse_error:
        print(f"  parse_error: {result.parse_error}")
        print(f"  raw_content: {result.raw_response.content[:300]}...")
        return 1

    print(json.dumps(result.output.model_dump(), indent=2))
    print(
        f"\n  tokens: prompt={result.raw_response.usage.prompt_tokens} "
        f"completion={result.raw_response.usage.completion_tokens}"
    )
    print(f"  latency: {result.raw_response.latency_ms}ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))