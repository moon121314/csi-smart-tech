"""HTTP endpoint for production state."""

import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ...core.database import get_db
from .service import calculate_production_state, calculate_state_summary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/state", tags=["state"])


@router.get("")
def get_state(
    source_id: str | None = Query(default=None, max_length=64),
    view: str = Query(default="full"),
    db: Session = Depends(get_db),
):
    """Return current production state. Optional source filter + summary view."""
    if view == "summary":
        model = calculate_state_summary(db, source_id=source_id)
    else:
        model = calculate_production_state(db, source_id=source_id)
    return JSONResponse(content=model.model_dump())
