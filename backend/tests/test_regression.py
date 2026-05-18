"""Tests for the regression diff between two runs."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.db_models import Base, EvalCase, EvalRun, RunStatus
from app.services.analysis.regression import (
    diff_runs,
    summarize_diff,
)


def _eval_run(prompt_version: str) -> EvalRun:
    return EvalRun(
        id=uuid.uuid4(),
        status=RunStatus.COMPLETED,
        prompt_version=prompt_version,
        model="m",
        provider="mock",
        dataset_path="d",
        dataset_size=1,
        notes="",
        summary_json={},
    )


def _case(
    run_id: uuid.UUID,
    case_id: str,
    passed: bool,
    judge: int | None = None,
    syco: float | None = None,
    uncert: float | None = None,
) -> EvalCase:
    return EvalCase(
        run_id=run_id,
        case_id=case_id,
        subset="x",
        passed=passed,
        approve_correct=passed,
        issues_caught=0,
        issues_expected=0,
        forbidden_keyword_hits=[],
        latency_ms=0,
        prompt_tokens=0,
        completion_tokens=0,
        judge_quality_score=judge,
        probe_is_sycophantic=syco,
        probe_is_uncertain=uncert,
        probe_is_refusing=None,
        probe_is_ungrounded=None,
    )


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


@pytest.mark.asyncio
async def test_no_regression_when_runs_identical(session: AsyncSession) -> None:
    run_a = _eval_run("v1")
    run_b = _eval_run("v2")
    session.add_all([run_a, run_b])
    await session.flush()
    session.add_all(
        [
            _case(run_a.id, "c1", passed=True, judge=8, syco=0.1, uncert=0.2),
            _case(run_b.id, "c1", passed=True, judge=8, syco=0.1, uncert=0.2),
        ]
    )
    await session.commit()

    diffs = await diff_runs(session, run_a.id, run_b.id)
    assert len(diffs) == 1
    assert diffs[0].overall_change == "unchanged"
    assert summarize_diff(diffs)["unchanged"] == 1


@pytest.mark.asyncio
async def test_deterministic_regression(session: AsyncSession) -> None:
    run_a = _eval_run("v1")
    run_b = _eval_run("v2")
    session.add_all([run_a, run_b])
    await session.flush()
    session.add_all(
        [
            _case(run_a.id, "c1", passed=True, judge=8),
            _case(run_b.id, "c1", passed=False, judge=8),
        ]
    )
    await session.commit()

    diffs = await diff_runs(session, run_a.id, run_b.id)
    assert diffs[0].deterministic_change == "regression"
    assert diffs[0].overall_change == "regression"


@pytest.mark.asyncio
async def test_judge_quality_drop_is_regression(session: AsyncSession) -> None:
    run_a = _eval_run("v1")
    run_b = _eval_run("v2")
    session.add_all([run_a, run_b])
    await session.flush()
    session.add_all(
        [
            _case(run_a.id, "c1", passed=True, judge=9),
            _case(run_b.id, "c1", passed=True, judge=6),
        ]
    )
    await session.commit()

    diffs = await diff_runs(session, run_a.id, run_b.id)
    assert diffs[0].judge_change == "regression"
    assert diffs[0].judge_delta == -3
    assert diffs[0].overall_change == "regression"


@pytest.mark.asyncio
async def test_probe_sycophancy_rise_is_regression(session: AsyncSession) -> None:
    run_a = _eval_run("v1")
    run_b = _eval_run("v2")
    session.add_all([run_a, run_b])
    await session.flush()
    session.add_all(
        [
            _case(run_a.id, "c1", passed=True, judge=8, syco=0.10),
            _case(run_b.id, "c1", passed=True, judge=8, syco=0.50),
        ]
    )
    await session.commit()

    diffs = await diff_runs(session, run_a.id, run_b.id)
    assert diffs[0].probe_changes["is_sycophantic"] == "regression"
    assert diffs[0].overall_change == "regression"


@pytest.mark.asyncio
async def test_mixed_when_some_improve_some_regress(session: AsyncSession) -> None:
    run_a = _eval_run("v1")
    run_b = _eval_run("v2")
    session.add_all([run_a, run_b])
    await session.flush()
    session.add_all(
        [
            _case(run_a.id, "c1", passed=False, judge=4, syco=0.5),
            _case(run_b.id, "c1", passed=True, judge=8, syco=0.7),
        ]
    )
    await session.commit()

    diffs = await diff_runs(session, run_a.id, run_b.id)
    assert diffs[0].deterministic_change == "improvement"
    assert diffs[0].probe_changes["is_sycophantic"] == "regression"
    assert diffs[0].overall_change == "mixed"


@pytest.mark.asyncio
async def test_missing_run_raises(session: AsyncSession) -> None:
    run_a = _eval_run("v1")
    session.add(run_a)
    await session.commit()

    with pytest.raises(ValueError, match="Run not found"):
        await diff_runs(session, run_a.id, uuid.uuid4())


@pytest.mark.asyncio
async def test_cases_only_in_one_run_are_ignored(session: AsyncSession) -> None:
    run_a = _eval_run("v1")
    run_b = _eval_run("v2")
    session.add_all([run_a, run_b])
    await session.flush()
    session.add_all(
        [
            _case(run_a.id, "shared", passed=True, judge=8),
            _case(run_a.id, "only_a", passed=True, judge=8),
            _case(run_b.id, "shared", passed=True, judge=8),
            _case(run_b.id, "only_b", passed=True, judge=8),
        ]
    )
    await session.commit()

    diffs = await diff_runs(session, run_a.id, run_b.id)
    assert len(diffs) == 1
    assert diffs[0].case_id == "shared"
