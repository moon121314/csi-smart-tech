"""Aggregation queries for the dashboard. No business logic."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ack.models import Acknowledgement
from ..events.models import ProductionEvent, SubmissionAttempt


def get_net_total(db: Session, source_id: str | None = None) -> int:
    """Sum of accepted COUNTs (voided COUNTs are excluded by status)."""
    stmt = select(func.coalesce(func.sum(ProductionEvent.quantity), 0)).where(
        ProductionEvent.event_type == "COUNT",
        ProductionEvent.status == "ACCEPTED",
    )
    if source_id is not None:
        stmt = stmt.where(ProductionEvent.source_id == source_id)
    return int(db.scalar(stmt) or 0)


def count_processed_events(db: Session, source_id: str | None = None) -> int:
    """Events that reached a settled state (ACCEPTED or VOIDED)."""
    stmt = select(func.count(ProductionEvent.id)).where(
        ProductionEvent.status.in_(["ACCEPTED", "VOIDED"])
    )
    if source_id is not None:
        stmt = stmt.where(ProductionEvent.source_id == source_id)
    return int(db.scalar(stmt) or 0)


def count_pending_ack(db: Session, source_id: str | None = None) -> int:
    """ACCEPTED events with no Acknowledgement row yet."""
    stmt = (
        select(func.count(ProductionEvent.id))
        .outerjoin(
            Acknowledgement,
            Acknowledgement.event_id == ProductionEvent.id,
        )
        .where(ProductionEvent.status == "ACCEPTED")
        .where(Acknowledgement.id.is_(None))
    )
    if source_id is not None:
        stmt = stmt.where(ProductionEvent.source_id == source_id)
    return int(db.scalar(stmt) or 0)


def count_unresolved(db: Session, source_id: str | None = None) -> int:
    """PENDING_REFERENCE events waiting for their target COUNT."""
    stmt = select(func.count(ProductionEvent.id)).where(
        ProductionEvent.status == "PENDING_REFERENCE"
    )
    if source_id is not None:
        stmt = stmt.where(ProductionEvent.source_id == source_id)
    return int(db.scalar(stmt) or 0)


def count_duplicates(db: Session, source_id: str | None = None) -> int:
    """SubmissionAttempts that returned DUPLICATE."""
    stmt = select(func.count(SubmissionAttempt.id)).where(
        SubmissionAttempt.result_status == "DUPLICATE"
    )
    if source_id is not None:
        stmt = stmt.where(SubmissionAttempt.source_id == source_id)
    return int(db.scalar(stmt) or 0)


def count_conflicts(db: Session, source_id: str | None = None) -> int:
    """SubmissionAttempts that returned CONFLICT."""
    stmt = select(func.count(SubmissionAttempt.id)).where(
        SubmissionAttempt.result_status == "CONFLICT"
    )
    if source_id is not None:
        stmt = stmt.where(SubmissionAttempt.source_id == source_id)
    return int(db.scalar(stmt) or 0)
