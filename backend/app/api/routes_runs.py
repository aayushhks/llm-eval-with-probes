"""Read-only API for browsing eval runs."""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_session
from app.models.db_models import EvalRun

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
