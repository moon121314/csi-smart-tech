"""HTTP endpoints for the events module."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from .schemas import BatchResponse, EventIn
from .service import process_batch

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
