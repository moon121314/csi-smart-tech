"""Pure data access for acknowledgements."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..events.models import ProductionEvent
from .models import Acknowledgement


def find_events_by_event_id(db: Session, event_id: str) -> list[ProductionEvent]:
    """Look up all events matching a user-facing event_id.

    Note: schema uniqueness is (source_id, event_id), so we may return
    more than one match if event_id is reused across sources.
    """
    return list(
        db.scalars(select(ProductionEvent).where(ProductionEvent.event_id == event_id))
    )


def get_acknowledgement_for_event(
    db: Session, internal_event_id: int
) -> Acknowledgement | None:
    return db.scalar(
        select(Acknowledgement).where(Acknowledgement.event_id == internal_event_id)
    )


def insert_acknowledgement(db: Session, ack: Acknowledgement) -> Acknowledgement:
    db.add(ack)
    db.flush()
    return ack
