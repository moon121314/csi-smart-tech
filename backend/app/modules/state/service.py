"""Business logic for the state endpoint."""

from sqlalchemy.orm import Session

from .repository import (
    count_conflicts,
    count_duplicates,
    count_pending_ack,
    count_processed_events,
    count_unresolved,
    get_net_total,
)
from .schemas import StateResponse, StateSummaryResponse


def calculate_production_state(
    db: Session, source_id: str | None = None
) -> StateResponse:
    """Full 6-field state payload."""
    return StateResponse(
        net_total=get_net_total(db, source_id),
        processed_events=count_processed_events(db, source_id),
        pending_ack=count_pending_ack(db, source_id),
        unresolved=count_unresolved(db, source_id),
        duplicates=count_duplicates(db, source_id),
        conflicts=count_conflicts(db, source_id),
    )


def calculate_state_summary(
    db: Session, source_id: str | None = None
) -> StateSummaryResponse:
    """Lightweight 3-field payload."""
    return StateSummaryResponse(
        net_total=get_net_total(db, source_id),
        pending_ack=count_pending_ack(db, source_id),
        processed_events=count_processed_events(db, source_id),
    )
