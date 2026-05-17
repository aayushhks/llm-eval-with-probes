"""Eval runner: orchestrates dataset → LLM → scorer → DB persistence."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aiolimiter import AsyncLimiter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.datasets.loader import load_dataset
from app.datasets.schemas import GoldenCase
from app.datasets.scorer import CaseScore, score_case
from app.features.code_review.service import ReviewResult, review_code_diff
from app.models.db_models import EvalCase, EvalRun, EvalTrace, RunStatus
from app.services.judge.schemas import JudgeOutput
from app.services.judge.service import JudgeResult, judge_review
from app.services.llm.base import LLMProvider
from app.services.llm.types import ProviderName

logger = get_logger("eval.runner")


@dataclass
class EvalRunConfig:
    prompt_version: str
    model: str
    provider_name: ProviderName
    dataset_path: Path | None = None
    case_ids: Sequence[str] | None = None  # if set, run only these
    subset: str | None = None  # if set, run only this subset
    concurrency: int = 1
    requests_per_minute: int = 20  # under Groq's 30 RPM cap
    notes: str = ""
    judge_enabled: bool = True
    judge_provider_name: ProviderName | None = None  # defaults to provider_name
    judge_model: str | None = None  # defaults to settings.default_judge_model
    judge_prompt_version: str = "v1"


@dataclass
class CaseExecution:
    case: GoldenCase
    review: ReviewResult
    score: CaseScore
    judge: JudgeResult | None = None


async def _judge_one(
    case: GoldenCase,
    review: ReviewResult,
    judge_provider: LLMProvider,
    judge_model: str,
    judge_prompt_version: str,
    limiter: AsyncLimiter,
    semaphore: asyncio.Semaphore,
) -> JudgeResult:
    async with semaphore, limiter:
        return await judge_review(
            case=case,
            review=review.output,
            provider=judge_provider,
            model=judge_model,
            prompt_version=judge_prompt_version,
        )


async def _execute_one(
    case: GoldenCase,
    provider: LLMProvider,
    model: str,
    prompt_version: str,
    limiter: AsyncLimiter,
    semaphore: asyncio.Semaphore,
) -> CaseExecution:
    async with semaphore, limiter:
        review = await review_code_diff(
            diff=case.diff,
            provider=provider,
            model=model,
            prompt_version=prompt_version,
        )
    score = score_case(case, review.output, review.parse_error)
    logger.info(
        "case_completed",
        case_id=case.id,
        subset=case.subset.value,
        passed=score.passed,
        latency_ms=review.raw_response.latency_ms,
    )
    return CaseExecution(case=case, review=review, score=score)


def _select_cases(config: EvalRunConfig) -> list[GoldenCase]:
    cases = load_dataset(config.dataset_path)
    if config.subset:
        cases = [c for c in cases if c.subset.value == config.subset]
    if config.case_ids:
        keep = set(config.case_ids)
        cases = [c for c in cases if c.id in keep]
    return cases


def _summarize(executions: list[CaseExecution]) -> dict[str, Any]:
    by_subset: dict[str, dict[str, int]] = {}
    total_passed = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0
    judge_quality_scores: list[int] = []
    judge_caught: list[bool] = []
    judge_invented: list[bool] = []
    judge_skeptical: list[bool] = []
    judge_prompt_tokens = 0
    judge_completion_tokens = 0

    for ex in executions:
        bucket = by_subset.setdefault(ex.case.subset.value, {"passed": 0, "total": 0})
        bucket["total"] += 1
        if ex.score.passed:
            bucket["passed"] += 1
            total_passed += 1
        total_prompt_tokens += ex.review.raw_response.usage.prompt_tokens
        total_completion_tokens += ex.review.raw_response.usage.completion_tokens
        if ex.judge and ex.judge.output:
            judge_quality_scores.append(ex.judge.output.quality_score)
            judge_caught.append(ex.judge.output.caught_real_issues)
            judge_invented.append(ex.judge.output.invented_issues)
            judge_skeptical.append(ex.judge.output.appropriately_skeptical)
            judge_prompt_tokens += ex.judge.raw_response.usage.prompt_tokens
            judge_completion_tokens += ex.judge.raw_response.usage.completion_tokens

    judge_summary: dict[str, Any] = {}
    if judge_quality_scores:
        judge_summary = {
            "n_judged": len(judge_quality_scores),
            "mean_quality": round(sum(judge_quality_scores) / len(judge_quality_scores), 2),
            "pct_caught_real_issues": round(sum(judge_caught) / len(judge_caught), 3),
            "pct_invented_issues": round(sum(judge_invented) / len(judge_invented), 3),
            "pct_appropriately_skeptical": round(sum(judge_skeptical) / len(judge_skeptical), 3),
            "tokens": {
                "prompt": judge_prompt_tokens,
                "completion": judge_completion_tokens,
            },
        }

    return {
        "total": len(executions),
        "passed": total_passed,
        "pass_rate": round((total_passed / len(executions)) if executions else 0.0, 3),
        "by_subset": by_subset,
        "tokens": {
            "prompt": total_prompt_tokens,
            "completion": total_completion_tokens,
        },
        "judge": judge_summary,
    }


async def run_eval(
    config: EvalRunConfig,
    provider: LLMProvider,
    session: AsyncSession,
) -> EvalRun:
    """Execute an eval run end-to-end and persist everything to Postgres."""
    cases = _select_cases(config)
    if not cases:
        raise ValueError("No cases selected for run")

    run = EvalRun(
        id=uuid.uuid4(),
        started_at=datetime.now(UTC),
        status=RunStatus.RUNNING,
        prompt_version=config.prompt_version,
        model=config.model,
        provider=config.provider_name.value,
        dataset_path=str(config.dataset_path or "default"),
        dataset_size=len(cases),
        notes=config.notes,
        summary_json={},
    )
    session.add(run)
    await session.flush()

    logger.info(
        "run_started",
        run_id=str(run.id),
        prompt=config.prompt_version,
        model=config.model,
        n_cases=len(cases),
    )

    limiter = AsyncLimiter(config.requests_per_minute, 60)
    semaphore = asyncio.Semaphore(config.concurrency)

    # Optional judge provider
    judge_provider: LLMProvider | None = None
    judge_model = config.judge_model or "llama-3.3-70b-versatile"
    if config.judge_enabled:
        from app.core.config import settings as _settings
        from app.services.llm.registry import get_provider

        jname = config.judge_provider_name or config.provider_name
        judge_provider = get_provider(jname)
        if not config.judge_model:
            judge_model = _settings.default_judge_model

    try:
        review_tasks = [
            _execute_one(
                case=case,
                provider=provider,
                model=config.model,
                prompt_version=config.prompt_version,
                limiter=limiter,
                semaphore=semaphore,
            )
            for case in cases
        ]
        executions = await asyncio.gather(*review_tasks)

        # Judge phase (sequential under same limiter to stay under rate caps)
        if config.judge_enabled and judge_provider is not None:
            judge_tasks = [
                _judge_one(
                    case=ex.case,
                    review=ex.review,
                    judge_provider=judge_provider,
                    judge_model=judge_model,
                    judge_prompt_version=config.judge_prompt_version,
                    limiter=limiter,
                    semaphore=semaphore,
                )
                for ex in executions
            ]
            judge_results = await asyncio.gather(*judge_tasks)
            for ex, jr in zip(executions, judge_results, strict=True):
                ex.judge = jr

        for ex in executions:
            judge_out: JudgeOutput | None = ex.judge.output if ex.judge else None
            case_row = EvalCase(
                run_id=run.id,
                case_id=ex.case.id,
                subset=ex.case.subset.value,
                passed=ex.score.passed,
                approve_correct=ex.score.approve_correct,
                issues_caught=ex.score.issues_caught,
                issues_expected=ex.score.issues_expected,
                forbidden_keyword_hits=ex.score.forbidden_keyword_hits,
                parse_error=ex.score.parse_error,
                latency_ms=ex.review.raw_response.latency_ms,
                prompt_tokens=ex.review.raw_response.usage.prompt_tokens,
                completion_tokens=ex.review.raw_response.usage.completion_tokens,
                judge_quality_score=judge_out.quality_score if judge_out else None,
                judge_caught_real_issues=judge_out.caught_real_issues if judge_out else None,
                judge_invented_issues=judge_out.invented_issues if judge_out else None,
                judge_appropriately_skeptical=(
                    judge_out.appropriately_skeptical if judge_out else None
                ),
                judge_reasoning=judge_out.reasoning if judge_out else None,
                judge_parse_error=ex.judge.parse_error if ex.judge else None,
                judge_latency_ms=ex.judge.raw_response.latency_ms if ex.judge else None,
                judge_prompt_tokens=(
                    ex.judge.raw_response.usage.prompt_tokens if ex.judge else None
                ),
                judge_completion_tokens=(
                    ex.judge.raw_response.usage.completion_tokens if ex.judge else None
                ),
            )
            session.add(case_row)
            await session.flush()

            trace = EvalTrace(
                case_row_id=case_row.id,
                request_messages=[
                    {"role": "system", "content": "<see prompt_version>"},
                    {"role": "user", "content": ex.case.diff},
                ],
                raw_response=ex.review.raw_response.content,
                parsed_review=ex.review.output.model_dump(mode="json"),
            )
            session.add(trace)

        run.summary_json = _summarize(executions)
        run.status = RunStatus.COMPLETED
        run.finished_at = datetime.now(UTC)
    except Exception as exc:
        run.status = RunStatus.FAILED
        run.finished_at = datetime.now(UTC)
        run.notes = (run.notes + f"\nerror: {exc}").strip()
        logger.exception("run_failed", run_id=str(run.id))
        await session.commit()
        raise

    await session.commit()
    await session.refresh(run, attribute_names=["cases"])
    logger.info(
        "run_completed",
        run_id=str(run.id),
        passed=run.summary_json.get("passed"),
        total=run.summary_json.get("total"),
    )
    return run
