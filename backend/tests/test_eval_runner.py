"""Tests for the eval runner using the mock provider against an in-memory SQLite DB."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.datasets.schemas import (
    DatasetSubset,
    ExpectedComment,
    GoldenCase,
)
from app.features.code_review.schemas import Category, Severity
from app.models.db_models import Base, RunStatus
from app.services.eval.runner import EvalRunConfig, run_eval
from app.services.llm.mock_provider import MockProvider
from app.services.llm.types import ProviderName


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """In-memory SQLite for fast isolated tests."""
    # SQLite doesn't support UUID natively but SQLAlchemy maps it to CHAR(32);
    # JSONB is fine because we declared it generically too.
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


def _make_case(
    case_id: str, subset: DatasetSubset, should_approve: bool, expects_issue: bool
) -> GoldenCase:
    issues = []
    if expects_issue:
        issues.append(
            ExpectedComment(
                must_mention=["password"],
                min_severity=Severity.WARNING,
                category=Category.SECURITY,
            )
        )
    return GoldenCase(
        id=case_id,
        subset=subset,
        description="x",
        diff="diff --git a/x.py b/x.py\n+password = 'x'\n",
        should_approve=should_approve,
        expected_issues=issues,
    )


class _CannedJsonProvider(MockProvider):
    """A mock that returns a fixed JSON review string."""

    def __init__(self, payload: str) -> None:
        super().__init__()
        self._payload = payload

    async def complete(self, request):  # type: ignore[override]
        response = await super().complete(request)
        response.content = self._payload
        return response


def _good_review_payload() -> str:
    return json.dumps(
        {
            "summary": "Hardcoded password is a security risk.",
            "approves": False,
            "comments": [
                {
                    "line_hint": "x.py password",
                    "severity": "blocker",
                    "category": "security",
                    "message": "The hardcoded password should be moved to env vars.",
                }
            ],
        }
    )


@pytest.mark.asyncio
async def test_run_eval_persists_run_with_cases(session: AsyncSession, tmp_path) -> None:
    # Write a tiny dataset file
    cases = [
        _make_case("c_001", DatasetSubset.CLEAR_ISSUES, False, True),
        _make_case("c_002", DatasetSubset.CLEAR_ISSUES, False, True),
    ]
    path = tmp_path / "ds.jsonl"
    with path.open("w") as f:
        for c in cases:
            f.write(json.dumps(c.model_dump(mode="json")) + "\n")

    provider = _CannedJsonProvider(_good_review_payload())
    config = EvalRunConfig(
        prompt_version="v1",
        model="mock-model",
        provider_name=ProviderName.MOCK,
        dataset_path=path,
        concurrency=2,
        requests_per_minute=600,  # disable for tests
    )

    run = await run_eval(config, provider, session)

    assert run.status == RunStatus.COMPLETED
    assert run.dataset_size == 2
    assert run.summary_json["total"] == 2
    assert run.summary_json["passed"] == 2
    assert run.summary_json["by_subset"]["clear_issues"]["passed"] == 2
    assert len(run.cases) == 2


@pytest.mark.asyncio
async def test_run_eval_records_failure_for_parse_error(session: AsyncSession, tmp_path) -> None:
    cases = [_make_case("c_001", DatasetSubset.CLEAR_ISSUES, False, True)]
    path = tmp_path / "ds.jsonl"
    with path.open("w") as f:
        for c in cases:
            f.write(json.dumps(c.model_dump(mode="json")) + "\n")

    provider = _CannedJsonProvider("not even json")
    config = EvalRunConfig(
        prompt_version="v1",
        model="mock-model",
        provider_name=ProviderName.MOCK,
        dataset_path=path,
        concurrency=1,
        requests_per_minute=600,
    )

    run = await run_eval(config, provider, session)
    assert run.status == RunStatus.COMPLETED  # run itself succeeded
    assert run.summary_json["passed"] == 0
    assert run.cases[0].parse_error is not None
    assert run.cases[0].passed is False


@pytest.mark.asyncio
async def test_run_eval_subset_filter(session: AsyncSession, tmp_path) -> None:
    cases = [
        _make_case("a_001", DatasetSubset.CLEAN, True, False),
        _make_case("a_002", DatasetSubset.CLEAR_ISSUES, False, True),
    ]
    path = tmp_path / "ds.jsonl"
    with path.open("w") as f:
        for c in cases:
            f.write(json.dumps(c.model_dump(mode="json")) + "\n")

    config = EvalRunConfig(
        prompt_version="v1",
        model="mock-model",
        provider_name=ProviderName.MOCK,
        dataset_path=path,
        subset="clean",
        concurrency=1,
        requests_per_minute=600,
    )

    provider = _CannedJsonProvider(json.dumps({"summary": "ok", "approves": True, "comments": []}))

    run = await run_eval(config, provider, session)
    assert run.dataset_size == 1
    assert len(run.cases) == 1
    assert run.cases[0].subset == "clean"
