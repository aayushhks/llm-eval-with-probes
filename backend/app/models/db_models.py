"""SQLAlchemy ORM models for eval runs, cases, and traces."""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import CHAR, TypeDecorator

JsonType = JSON().with_variant(JSONB(), "postgresql")


class GUID(TypeDecorator):  # type: ignore[type-arg]
    """Platform-independent UUID. PG_UUID on Postgres, CHAR(32) elsewhere."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):  # type: ignore[no-untyped-def]
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):  # type: ignore[no-untyped-def]
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        if isinstance(value, uuid.UUID):
            return value.hex
        return uuid.UUID(value).hex

    def process_result_value(self, value, dialect):  # type: ignore[no-untyped-def]
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(value)


class Base(DeclarativeBase):
    pass


class RunStatus(enum.StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"), nullable=False, default=RunStatus.RUNNING
    )

    prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)

    dataset_path: Mapped[str] = mapped_column(String(512), nullable=False)
    dataset_size: Mapped[int] = mapped_column(Integer, nullable=False)

    notes: Mapped[str] = mapped_column(Text, default="")
    summary_json: Mapped[dict[str, Any]] = mapped_column(JsonType, default=dict)

    cases: Mapped[list[EvalCase]] = relationship(
        "EvalCase", back_populates="run", cascade="all, delete-orphan"
    )


class EvalCase(Base):
    __tablename__ = "eval_cases"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    run_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False
    )
    case_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subset: Mapped[str] = mapped_column(String(64), nullable=False)

    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    approve_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    issues_caught: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    issues_expected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    forbidden_keyword_hits: Mapped[list[str]] = mapped_column(JSON, default=list)
    parse_error: Mapped[str | None] = mapped_column(Text)

    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    run: Mapped[EvalRun] = relationship("EvalRun", back_populates="cases")
    trace: Mapped[EvalTrace | None] = relationship(
        "EvalTrace", back_populates="case", uselist=False, cascade="all, delete-orphan"
    )


class EvalTrace(Base):
    __tablename__ = "eval_traces"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    case_row_id: Mapped[uuid.UUID] = mapped_column(
        GUID(), ForeignKey("eval_cases.id", ondelete="CASCADE"), nullable=False
    )
    request_messages: Mapped[list[dict[str, Any]]] = mapped_column(JsonType, nullable=False)
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_review: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)

    case: Mapped[EvalCase] = relationship("EvalCase", back_populates="trace")
