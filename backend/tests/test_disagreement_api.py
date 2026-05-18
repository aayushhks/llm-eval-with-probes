"""Tests for the /runs/{id}/disagreements endpoint."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_session
from app.main import app
from app.models.db_models import Base, EvalCase, EvalRun, EvalTrace, RunStatus


@pytest_asyncio.fixture
async def session_and_run() -> AsyncIterator[tuple[AsyncSession, uuid.UUID]]:
    """In-memory SQLite engine with one fully-populated run."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)

    run_id = uuid.uuid4()
    async with Session() as session:
        run = EvalRun(
            id=run_id,
            status=RunStatus.COMPLETED,
            prompt_version="v1",
            model="mock-model",
            provider="mock",
            dataset_path="t",
            dataset_size=2,
            notes="",
            summary_json={},
        )
        session.add(run)
        await session.flush()

        # Case 1: det-fail, judge-good, probe-high — should be high priority
        bad_case = EvalCase(
            run_id=run.id,
            case_id="bad_001",
            subset="sycophancy_bait",
            passed=False,
            approve_correct=False,
            issues_caught=0,
            issues_expected=1,
            forbidden_keyword_hits=[],
            latency_ms=10,
            prompt_tokens=10,
            completion_tokens=10,
            judge_quality_score=9,
            judge_caught_real_issues=False,
            judge_invented_issues=False,
            judge_appropriately_skeptical=False,
            judge_reasoning="Looks fine to me.",
            judge_latency_ms=20,
            judge_prompt_tokens=20,
            judge_completion_tokens=20,
            probe_is_sycophantic=0.55,
            probe_is_refusing=0.05,
            probe_is_ungrounded=0.6,
            probe_is_uncertain=0.75,
        )
        session.add(bad_case)
        await session.flush()

        bad_trace = EvalTrace(
            case_row_id=bad_case.id,
            request_messages=[{"role": "user", "content": "diff"}],
            raw_response='{"summary":"LGTM","approves":true,"comments":[]}',
            parsed_review={"summary": "LGTM", "approves": True, "comments": []},
        )
        session.add(bad_trace)

        # Case 2: clean agreement, no flags
        clean_case = EvalCase(
            run_id=run.id,
            case_id="clean_001",
            subset="clean",
            passed=True,
            approve_correct=True,
            issues_caught=0,
            issues_expected=0,
            forbidden_keyword_hits=[],
            latency_ms=10,
            prompt_tokens=10,
            completion_tokens=10,
            judge_quality_score=9,
            judge_caught_real_issues=True,
            judge_invented_issues=False,
            judge_appropriately_skeptical=True,
            judge_reasoning="Good review of a clean diff.",
            probe_is_sycophantic=0.05,
            probe_is_refusing=0.02,
            probe_is_ungrounded=0.1,
            probe_is_uncertain=0.1,
        )
        session.add(clean_case)
        await session.commit()

        yield session, run_id

    await engine.dispose()


@pytest.mark.asyncio
async def test_disagreements_endpoint(
    session_and_run: tuple[AsyncSession, uuid.UUID],
) -> None:
    session, run_id = session_and_run

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/runs/{run_id}/disagreements")
        assert resp.status_code == 200
        body = resp.json()
        assert body["run_id"] == str(run_id)
        assert body["total_cases"] == 2
        assert body["flagged_cases"] == 1
        assert body["disagreements"][0]["case_id"] == "bad_001"

        flags = body["disagreements"][0]["flags"]
        assert "det_fail_judge_good" in flags
        assert "probe_says_sycophantic_judge_says_fine" in flags
        assert "probe_says_uncertain_judge_says_fine" in flags

        # raw review text is included for frontend display
        assert body["disagreements"][0]["raw_review"] is not None
        assert "LGTM" in body["disagreements"][0]["raw_review"]

        # judge reasoning is included
        assert body["disagreements"][0]["judge_reasoning"] == "Looks fine to me."

        # priority ranking puts probe-says-syco-judge-says-fine first
        assert body["disagreements"][0]["priority"] >= 100

        # flag totals
        assert body["flag_totals"]["det_fail_judge_good"] == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_disagreements_unknown_run_returns_404(
    session_and_run: tuple[AsyncSession, uuid.UUID],
) -> None:
    session, _ = session_and_run

    async def override_get_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/runs/{uuid.uuid4()}/disagreements")
        # The analyzer raises ValueError; FastAPI returns 500 by default.
        # We expect either 404 (if we catch it) or 500 — either is acceptable
        # for v1. We'll improve in a later milestone if needed.
        assert resp.status_code == 404
    finally:
        app.dependency_overrides.clear()
