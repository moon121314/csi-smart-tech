"""Pure data access for events. No business logic lives here."""

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..sources.models import ProductionSource
from .models import ProductionEvent, SubmissionAttempt


def get_source_by_source_id(db: Session, source_id: str) -> ProductionSource | None:
    return db.scalar(
        select(ProductionSource).where(ProductionSource.source_id == source_id)
    )


def get_event_by_source_and_event_id(
    db: Session, source_id: str, event_id: str
) -> ProductionEvent | None:
    return db.scalar(
        select(ProductionEvent)
        .where(ProductionEvent.source_id == source_id)
        .where(ProductionEvent.event_id == event_id)
    )


def insert_event(db: Session, event: ProductionEvent) -> ProductionEvent:
    """Insert and flush. IntegrityError propagates to the caller."""
    db.add(event)
    db.flush()
    return event


def insert_attempt(db: Session, attempt: SubmissionAttempt) -> None:
    """Queue an attempt record for insert. Flushed at savepoint/commit."""
    db.add(attempt)


def advisory_lock_for_event(db: Session, source_id: str, event_id: str) -> None:
    """
    Transaction-scoped PostgreSQL advisory lock keyed on
    (source_id, event_id). Serializes concurrent COUNT-insert and
    VOID-pending for the same key. Auto-released at commit/rollback.
    """
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:s), hashtext(:e))"),
        {"s": source_id, "e": event_id},
    )


def get_event_for_update(
    db: Session, source_id: str, event_id: str
) -> ProductionEvent | None:
    """SELECT ... FOR UPDATE — locks the target row for this transaction."""
    return db.scalar(
        select(ProductionEvent)
        .where(ProductionEvent.source_id == source_id)
        .where(ProductionEvent.event_id == event_id)
        .with_for_update()
    )


def get_pending_voids_for_target(
    db: Session, source_id: str, target_event_id: str
) -> list[ProductionEvent]:
    """Pending VOIDs pointing at the given (source_id, target_event_id)."""
    return list(
        db.scalars(
            select(ProductionEvent)
            .where(ProductionEvent.source_id == source_id)
            .where(ProductionEvent.event_type == "VOID")
            .where(ProductionEvent.target_event_id == target_event_id)
            .where(ProductionEvent.status == "PENDING_REFERENCE")
            .order_by(ProductionEvent.id)
        )
    )
