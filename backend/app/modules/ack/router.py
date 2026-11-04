"""HTTP endpoint for acknowledgements."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.database import get_db
from .schemas import AckRequest, AckResponse
from .service import process_acks

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ack", tags=["ack"])


@router.post("", response_model=AckResponse, response_model_exclude_none=True)
def submit_acks(payload: AckRequest, db: Session = Depends(get_db)) -> AckResponse:
    """Acknowledge one or more events by event_id."""
    results = process_acks(db, payload.event_ids, payload.acknowledged_by)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return AckResponse(results=results)
