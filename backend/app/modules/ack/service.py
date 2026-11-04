"""Business logic for supervisor acknowledgements."""

import logging

from sqlalchemy.orm import Session

from .models import Acknowledgement
from .repository import (
    find_events_by_event_id,
    get_acknowledgement_for_event,
    insert_acknowledgement,
)
from .schemas import AckResult

logger = logging.getLogger(__name__)


def acknowledge_event(
    db: Session, event_id_str: str, acknowledged_by: str
) -> AckResult:
    """Acknowledge one event. Idempotent. Never raises for business paths."""
    matches = find_events_by_event_id(db, event_id_str)

    if len(matches) == 0:
        return AckResult(
            event_id=event_id_str,
            status="NOT_FOUND",
            message=f"Event '{event_id_str}' not found",
            error_code="EVENT_NOT_FOUND",
        )

    if len(matches) > 1:
        return AckResult(
            event_id=event_id_str,
            status="AMBIGUOUS_EVENT_ID",
            message=(
                f"Multiple events match event_id '{event_id_str}'; "
                f"cannot acknowledge unambiguously"
            ),
            error_code="AMBIGUOUS_EVENT_ID",
        )

    event = matches[0]

    if event.status != "ACCEPTED":
        return AckResult(
            event_id=event_id_str,
            status="NOT_ELIGIBLE",
            message=(f"Event with status '{event.status}' is not acknowledgeable"),
            error_code="NOT_ELIGIBLE",
        )

    existing = get_acknowledgement_for_event(db, event.id)
    if existing is not None:
        return AckResult(
            event_id=event_id_str,
            status="ALREADY_ACKNOWLEDGED",
            message=(f"Event already acknowledged by " f"'{existing.acknowledged_by}'"),
        )

    ack = Acknowledgement(
        event_id=event.id,
        acknowledged_by=acknowledged_by,
        status="ACKNOWLEDGED",
    )
    insert_acknowledgement(db, ack)

    return AckResult(
        event_id=event_id_str,
        status="ACKNOWLEDGED",
        message=f"Event acknowledged by '{acknowledged_by}'",
    )


def process_acks(
    db: Session, event_ids: list[str], acknowledged_by: str
) -> list[AckResult]:
    """Process each event_id in its own SAVEPOINT."""
    results: list[AckResult] = []

    for event_id_str in event_ids:
        savepoint = db.begin_nested()
        try:
            result = acknowledge_event(db, event_id_str, acknowledged_by)
            savepoint.commit()
        except Exception as exc:
            savepoint.rollback()
            logger.exception(
                "ack.failed",
                extra={"event_id": event_id_str, "error": str(exc)},
            )
            result = AckResult(
                event_id=event_id_str,
                status="ERROR",
                message="Internal error acknowledging event",
                error_code="INTERNAL_ERROR",
            )
        results.append(result)

    return results
