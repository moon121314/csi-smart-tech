"""Pure data access for events. No business logic lives here."""

from sqlalchemy import select
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
