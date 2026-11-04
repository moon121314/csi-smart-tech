"""HTTP endpoints for the events module."""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...core.database import get_db
from .schemas import BatchResponse, EventIn, EventListResponse, EventOut
from .service import list_events_with_ack, process_batch

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["events"])


@router.post(
    "",
    response_model=BatchResponse,
    response_model_exclude_none=True,
)
def submit_events(
    payload: EventIn | list[EventIn],
    db: Session = Depends(get_db),
) -> BatchResponse:
    """Accept a single event or a list of events."""
    events = payload if isinstance(payload, list) else [payload]
    try:
        results = process_batch(db, events)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return BatchResponse(results=results)


@router.get("", response_model=EventListResponse)
def get_events(
    limit: int = Query(default=50, ge=1, le=500),
    status: str | None = Query(default=None, max_length=32),
    include_voided: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> EventListResponse:
    """List recent events for the dashboard."""
    rows = list_events_with_ack(
        db,
        status_filter=status,
        include_voided=include_voided,
        limit=limit,
    )
    return EventListResponse(events=[EventOut(**r) for r in rows])
