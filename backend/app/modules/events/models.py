"""ProductionEvent and SubmissionAttempt ORM models."""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db_base import Base


class ProductionEvent(Base):
    """A single production event (COUNT or VOID) that has been persisted."""

    __tablename__ = "production_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("production_sources.source_id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    target_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default="ACCEPTED"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "source_id", "event_id", name="uq_production_events_source_event"
        ),
        CheckConstraint(
            "event_type IN ('COUNT', 'VOID')",
            name="ck_production_events_type",
        ),
        CheckConstraint(
            "(event_type = 'COUNT' AND quantity > 0) "
            "OR (event_type = 'VOID' AND quantity >= 0)",
            name="ck_production_events_quantity",
        ),
        CheckConstraint(
            "status IN ('ACCEPTED', 'VOIDED', 'PENDING_REFERENCE')",
            name="ck_production_events_status",
        ),
        Index("ix_production_events_source_status", "source_id", "status"),
        Index(
            "ix_production_events_source_target",
            "source_id",
            "target_event_id",
        ),
        Index("ix_production_events_event_time", "event_time"),
    )

    def __repr__(self) -> str:
        return (
            f"<ProductionEvent id={self.id} source_id={self.source_id!r} "
            f"event_id={self.event_id!r} type={self.event_type} status={self.status}>"
        )


class SubmissionAttempt(Base):
    """
    Audit trail of every incoming submission, including duplicates and rejections.

    NOTE: `source_id` has NO foreign key on purpose — we must record attempts
    for unknown sources too (those get result_status='REJECTED').
    """

    __tablename__ = "submission_attempts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    request_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result_status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_submission_attempts_source_event", "source_id", "event_id"),
        Index("ix_submission_attempts_received_at", "received_at"),
        Index("ix_submission_attempts_result_status", "result_status"),
    )

    def __repr__(self) -> str:
        return (
            f"<SubmissionAttempt id={self.id} "
            f"source_id={self.source_id!r} event_id={self.event_id!r} "
            f"result={self.result_status}>"
        )
