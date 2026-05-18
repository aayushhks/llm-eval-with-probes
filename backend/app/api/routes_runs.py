"""Read-only API for browsing eval runs."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.models.db_models import EvalCase, EvalRun
from app.services.analysis.disagreement import analyze_run

router = APIRouter(prefix="/runs", tags=["runs"])

# Type alias for the injected session
SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("")
async def list_runs(
    session: SessionDep,
    limit: int = 50,
) -> list[dict[str, Any]]:
    result = await session.execute(select(EvalRun).order_by(desc(EvalRun.started_at)).limit(limit))
    runs = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "started_at": r.started_at.isoformat(),
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "status": r.status.value,
            "prompt_version": r.prompt_version,
            "model": r.model,
            "provider": r.provider,
            "dataset_size": r.dataset_size,
            "summary": r.summary_json,
            "notes": r.notes,
        }
        for r in runs
    ]


@router.get("/{run_id}")
async def get_run(
    run_id: uuid.UUID,
    session: SessionDep,
) -> dict[str, Any]:
    result = await session.execute(
        select(EvalRun).where(EvalRun.id == run_id).options(selectinload(EvalRun.cases))
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    return {
        "id": str(run.id),
        "started_at": run.started_at.isoformat(),
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "status": run.status.value,
        "prompt_version": run.prompt_version,
        "model": run.model,
        "provider": run.provider,
        "dataset_size": run.dataset_size,
        "summary": run.summary_json,
        "notes": run.notes,
        "cases": [
            {
                "case_id": c.case_id,
                "subset": c.subset,
                "passed": c.passed,
                "approve_correct": c.approve_correct,
                "issues_caught": c.issues_caught,
                "issues_expected": c.issues_expected,
                "forbidden_keyword_hits": c.forbidden_keyword_hits,
                "parse_error": c.parse_error,
                "latency_ms": c.latency_ms,
                "tokens": {
                    "prompt": c.prompt_tokens,
                    "completion": c.completion_tokens,
                },
                "judge": {
                    "quality_score": c.judge_quality_score,
                    "caught_real_issues": c.judge_caught_real_issues,
                    "invented_issues": c.judge_invented_issues,
                    "appropriately_skeptical": c.judge_appropriately_skeptical,
                    "reasoning": c.judge_reasoning,
                    "parse_error": c.judge_parse_error,
                    "latency_ms": c.judge_latency_ms,
                    "tokens": {
                        "prompt": c.judge_prompt_tokens,
                        "completion": c.judge_completion_tokens,
                    },
                    "probes": {
                        "is_sycophantic": c.probe_is_sycophantic,
                        "is_refusing": c.probe_is_refusing,
                        "is_ungrounded": c.probe_is_ungrounded,
                        "is_uncertain": c.probe_is_uncertain,
                    },
                },
            }
            for c in run.cases
        ],
    }


@router.get("/{run_id}/disagreements")
async def get_disagreements(
    run_id: uuid.UUID,
    session: SessionDep,
) -> dict[str, Any]:
    """Per-case disagreement view: cases where scorers reached different conclusions.

    Sorted with the most striking disagreements first (probe-vs-judge first,
    then det-vs-judge, then probe corroborations of deterministic failures).
    """
    try:
        rows = await analyze_run(session, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # Pull the run + the diff + raw review for each case from the same session.
    # We need to re-query for the raw review text since CaseRow doesn't carry it.
    stmt = (
        select(EvalRun)
        .where(EvalRun.id == run_id)
        .options(selectinload(EvalRun.cases).selectinload(EvalCase.trace))
    )
    result = await session.execute(stmt)
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    cases_by_id = {c.case_id: c for c in run.cases}

    # Priority ranking for sorting: higher rank = more striking
    def priority(flags: list[str]) -> int:
        score = 0
        if "probe_says_sycophantic_judge_says_fine" in flags:
            score += 100
        if "probe_says_uncertain_judge_says_fine" in flags:
            score += 80
        if "probe_says_ungrounded_judge_says_fine" in flags:
            score += 60
        if "det_fail_judge_good" in flags:
            score += 50
        if "det_pass_judge_bad" in flags:
            score += 40
        if "probe_confirms_failure_via_sycophancy" in flags:
            score += 20
        if "probe_confirms_failure_via_uncertainty" in flags:
            score += 15
        return score

    items = []
    for r in rows:
        if not r.flags:
            continue
        case_obj = cases_by_id.get(r.case_id)
        items.append(
            {
                "case_id": r.case_id,
                "subset": r.subset,
                "deterministic_passed": r.deterministic_passed,
                "judge_quality": r.judge_quality,
                "judge_reasoning": (case_obj.judge_reasoning if case_obj else None),
                "probes": {
                    "is_sycophantic": r.probe_sycophantic,
                    "is_refusing": r.probe_refusing,
                    "is_ungrounded": r.probe_ungrounded,
                    "is_uncertain": r.probe_uncertain,
                },
                "flags": r.flags,
                "priority": priority(r.flags),
                "raw_review": (
                    case_obj.trace.raw_response if case_obj and case_obj.trace else None
                ),
            }
        )

    items.sort(key=lambda x: x["priority"], reverse=True)  # type: ignore[arg-type,return-value]

    flag_totals: dict[str, int] = {}
    for r in rows:
        for f in r.flags:
            flag_totals[f] = flag_totals.get(f, 0) + 1

    return {
        "run_id": str(run_id),
        "prompt_version": run.prompt_version,
        "model": run.model,
        "total_cases": len(rows),
        "flagged_cases": len(items),
        "flag_totals": flag_totals,
        "disagreements": items,
    }
