"""Event processing business logic. Not HTTP, not raw SQL."""

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..common.enums import SubmissionResult
from .exceptions import InvalidEventError, SourceNotFoundError
from .models import ProductionEvent, SubmissionAttempt
from .repository import (
    advisory_lock_for_event,
    get_event_by_source_and_event_id,
    get_event_for_update,
    get_pending_voids_for_target,
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
    if (
        event.type == "VOID"
        and event.target_event_id is not None
        and event.target_event_id == event.event_id
    ):
        raise InvalidEventError("VOID cannot target itself", "SELF_REFERENCE_TARGET")


def _matches(existing: ProductionEvent, incoming: EventIn) -> bool:
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


def _process_count(db: Session, event: EventIn) -> EventResult:
    """Insert COUNT; auto-resolve any pending VOID that targets it."""
    advisory_lock_for_event(db, event.source_id, event.event_id)

    db_event = ProductionEvent(
        source_id=event.source_id,
        event_id=event.event_id,
        event_type="COUNT",
        quantity=event.quantity,
        target_event_id=None,
        event_time=event.event_time,
        status="ACCEPTED",
    )
    insert_event(db, db_event)

    pending_voids = get_pending_voids_for_target(db, event.source_id, event.event_id)
    if pending_voids:
        pending_void = pending_voids[0]
        db_event.status = "VOIDED"
        pending_void.status = "ACCEPTED"
        db.flush()
        logger.info(
            "void.auto_resolved",
            extra={
                "source_id": event.source_id,
                "count_event_id": event.event_id,
                "void_event_id": pending_void.event_id,
                "resolution": "PENDING_VOID_RESOLVED",
            },
        )
        return EventResult(
            event_id=event.event_id,
            status=SubmissionResult.ACCEPTED.value,
            message=("Production count accepted; matching pending VOID resolved"),
        )

    return EventResult(
        event_id=event.event_id,
        status=SubmissionResult.ACCEPTED.value,
        message="Production count accepted",
    )


def _process_void(db: Session, event: EventIn) -> EventResult:
    """Validate and resolve a VOID against its target COUNT."""
    target_event_id = event.target_event_id
    if target_event_id is None:
        # Defensive — validate_event already rejects this case
        return EventResult(
            event_id=event.event_id,
            status=SubmissionResult.REJECTED.value,
            message="VOID missing target_event_id",
            error_code="MISSING_TARGET",
        )

    advisory_lock_for_event(db, event.source_id, target_event_id)

    target = get_event_for_update(db, event.source_id, target_event_id)

    if target is None:
        existing_pending = get_pending_voids_for_target(
            db, event.source_id, target_event_id
        )
        if existing_pending:
            return EventResult(
                event_id=event.event_id,
                status=SubmissionResult.REJECTED.value,
                message=("A pending VOID already exists for this target_event_id"),
                error_code="DUPLICATE_PENDING_VOID",
            )

        db_event = ProductionEvent(
            source_id=event.source_id,
            event_id=event.event_id,
            event_type="VOID",
            quantity=event.quantity,
            target_event_id=target_event_id,
            event_time=event.event_time,
            status="PENDING_REFERENCE",
        )
        insert_event(db, db_event)
        return EventResult(
            event_id=event.event_id,
            status=SubmissionResult.PENDING_REFERENCE.value,
            message=(
                f"Target COUNT '{target_event_id}' not yet received; "
                f"VOID stored as pending"
            ),
        )

    if target.event_type != "COUNT":
        return EventResult(
            event_id=event.event_id,
            status=SubmissionResult.REJECTED.value,
            message=f"Cannot void a {target.event_type} event",
            error_code="INVALID_TARGET_TYPE",
        )

    if target.status != "ACCEPTED":
        return EventResult(
            event_id=event.event_id,
            status=SubmissionResult.REJECTED.value,
            message=(
                f"Target COUNT is not voidable " f"(current status: {target.status})"
            ),
            error_code="TARGET_NOT_VOIDABLE",
        )

    if target.source_id != event.source_id:
        return EventResult(
            event_id=event.event_id,
            status=SubmissionResult.REJECTED.value,
            message="VOID and target COUNT must belong to the same source",
            error_code="SOURCE_MISMATCH",
        )

    target.status = "VOIDED"
    db_event = ProductionEvent(
        source_id=event.source_id,
        event_id=event.event_id,
        event_type="VOID",
        quantity=event.quantity,
        target_event_id=target_event_id,
        event_time=event.event_time,
        status="ACCEPTED",
    )
    insert_event(db, db_event)

    return EventResult(
        event_id=event.event_id,
        status=SubmissionResult.ACCEPTED.value,
        message="Void accepted",
    )


def process_event(db: Session, event: EventIn) -> EventResult:
    """Process a single event. Returns an EventResult for every path."""
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

    if event.type == "COUNT":
        result = _process_count(db, event)
    else:
        result = _process_void(db, event)

    _record_attempt(db, event, result)
    return result


def process_batch(db: Session, events: list[EventIn]) -> list[EventResult]:
    """Process events in submission order, one SAVEPOINT per event."""
    results: list[EventResult] = []

    for event in events:
        savepoint = db.begin_nested()
        try:
            result = process_event(db, event)
            savepoint.commit()
        except IntegrityError:
            savepoint.rollback()
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
                message="Internal error processing event",
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
