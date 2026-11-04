"""Event processing business logic. Not HTTP, not raw SQL."""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..common.enums import SubmissionResult
from .exceptions import InvalidEventError, SourceNotFoundError
from .models import ProductionEvent, SubmissionAttempt
from .repository import (
    get_event_by_source_and_event_id,
    get_source_by_source_id,
    insert_attempt,
    insert_event,
)
from .schemas import EventIn, EventResult

logger = logging.getLogger(__name__)


VALID_EVENT_TYPES = {"COUNT", "VOID"}


def validate_event(event: EventIn) -> None:
    """Raise InvalidEventError if the event violates business rules."""
    if event.type not in VALID_EVENT_TYPES:
        raise InvalidEventError(f"Unknown event type: {event.type}", "INVALID_TYPE")
    if event.type == "COUNT" and event.quantity <= 0:
        raise InvalidEventError(
            "COUNT quantity must be greater than 0", "INVALID_QUANTITY"
        )
    if event.type == "VOID" and event.quantity < 0:
        raise InvalidEventError("VOID quantity cannot be negative", "INVALID_QUANTITY")
    if event.type == "VOID" and not event.target_event_id:
        raise InvalidEventError(
            "VOID must reference a target_event_id", "MISSING_TARGET"
        )
    if event.type == "COUNT" and event.target_event_id is not None:
        raise InvalidEventError(
            "COUNT must not have a target_event_id", "UNEXPECTED_TARGET"
        )


def _matches(existing: ProductionEvent, incoming: EventIn) -> bool:
    """True if the DB row represents the same logical event as `incoming`."""
    return (
        existing.event_type == incoming.type
        and existing.quantity == incoming.quantity
        and existing.target_event_id == incoming.target_event_id
        and existing.event_time == incoming.event_time
    )


def _record_attempt(db: Session, event: EventIn, result: EventResult) -> None:
    try:
        attempt = SubmissionAttempt(
            source_id=event.source_id,
            event_id=event.event_id,
            event_type=event.type if event.type in VALID_EVENT_TYPES else None,
            request_payload=event.model_dump(mode="json"),
            result_status=result.status,
            error_code=result.error_code,
        )
        insert_attempt(db, attempt)
    except Exception as exc:  # pragma: no cover
        logger.error(
            "attempt.record_failed",
            extra={"event_id": event.event_id, "error": str(exc)},
        )


def process_event(db: Session, event: EventIn) -> EventResult:
    """
    Process a single event. Returns an EventResult for every path.
    Does NOT catch IntegrityError — that is handled by `process_batch`.

    Assumes caller has begun a SAVEPOINT and will commit/rollback it.
    """
    # 1. Business validation
    try:
        validate_event(event)
    except InvalidEventError as exc:
        result = EventResult(
            event_id=event.event_id,
            status=SubmissionResult.REJECTED.value,
            message=exc.message,
            error_code=exc.error_code,
        )
        _record_attempt(db, event, result)
        return result

    # 2. Source must exist
    try:
        if get_source_by_source_id(db, event.source_id) is None:
            raise SourceNotFoundError(event.source_id)
    except SourceNotFoundError as exc:
        result = EventResult(
            event_id=event.event_id,
            status=SubmissionResult.REJECTED.value,
            message=exc.message,
            error_code=exc.error_code,
        )
        _record_attempt(db, event, result)
        return result

    # 3. Duplicate / conflict detection
    existing = get_event_by_source_and_event_id(db, event.source_id, event.event_id)
    if existing is not None:
        if _matches(existing, event):
            result = EventResult(
                event_id=event.event_id,
                status=SubmissionResult.DUPLICATE.value,
                message="Event already received with identical content",
            )
        else:
            result = EventResult(
                event_id=event.event_id,
                status=SubmissionResult.CONFLICT.value,
                message="Event ID already used with different content",
                error_code="CONFLICT",
            )
        _record_attempt(db, event, result)
        return result

    # 4. Insert (may raise IntegrityError under concurrency — handled by batch)
    db_event = ProductionEvent(
        source_id=event.source_id,
        event_id=event.event_id,
        event_type=event.type,
        quantity=event.quantity,
        target_event_id=event.target_event_id,
        event_time=event.event_time,
        status="ACCEPTED",
    )
    insert_event(db, db_event)

    result = EventResult(
        event_id=event.event_id,
        status=SubmissionResult.ACCEPTED.value,
        message=(
            "Production count accepted" if event.type == "COUNT" else "Void accepted"
        ),
    )
    _record_attempt(db, event, result)
    return result


def process_batch(db: Session, events: list[EventIn]) -> list[EventResult]:
    """
    Process events one by one. Each is its own SAVEPOINT — one failure
    does not prevent other events in the batch from being processed.
    """
    results: list[EventResult] = []

    for event in events:
        savepoint = db.begin_nested()
        try:
            result = process_event(db, event)
            savepoint.commit()
        except IntegrityError:
            savepoint.rollback()
            # A concurrent writer inserted the same (source, event_id)
            existing = get_event_by_source_and_event_id(
                db, event.source_id, event.event_id
            )
            if existing is not None and _matches(existing, event):
                result = EventResult(
                    event_id=event.event_id,
                    status=SubmissionResult.DUPLICATE.value,
                    message="Event already received (concurrent)",
                )
            else:
                result = EventResult(
                    event_id=event.event_id,
                    status=SubmissionResult.CONFLICT.value,
                    message="Event ID already used with different content",
                    error_code="CONFLICT",
                )
            # Record the attempt in its own savepoint
            sp2 = db.begin_nested()
            try:
                _record_attempt(db, event, result)
                sp2.commit()
            except Exception:
                sp2.rollback()
        except Exception as exc:
            savepoint.rollback()
            logger.exception(
                "event.process_failed",
                extra={"event_id": event.event_id, "error": str(exc)},
            )
            result = EventResult(
                event_id=event.event_id,
                status=SubmissionResult.REJECTED.value,
                message=f"Internal error processing event",
                error_code="INTERNAL_ERROR",
            )
            sp2 = db.begin_nested()
            try:
                _record_attempt(db, event, result)
                sp2.commit()
            except Exception:
                sp2.rollback()

        results.append(result)

    return results
