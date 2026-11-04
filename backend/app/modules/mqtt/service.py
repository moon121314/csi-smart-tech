"""MQTT message handlers.

Reuses the same events.service.process_batch as the REST API — one
shared processing pipeline, no duplicated business logic.
"""

import logging
from datetime import datetime, timezone

from ...core.config import settings
from ...core.database import SessionLocal
from ..events.schemas import EventIn
from ..events.service import process_batch
from .client import MQTTClient
from .models import MQTTChallenge
from .schemas import ChallengePayload
from .wire_format import (
    build_challenge_response,
    build_event_failure_response,
    build_event_success_response,
)

logger = logging.getLogger(__name__)


def handle_challenge(client: MQTTClient, payload: dict) -> None:
    """Idempotent challenge handling. Publishes response only once per id."""
    try:
        chal = ChallengePayload.model_validate(payload)
    except Exception as exc:
        logger.error("mqtt.challenge.invalid", extra={"error": str(exc)})
        return

    with SessionLocal() as db:
        existing = (
            db.query(MQTTChallenge)
            .filter(MQTTChallenge.challenge_id == chal.challenge_id)
            .one_or_none()
        )
        if existing is not None and existing.status == "RESPONDED":
            logger.info(
                "mqtt.challenge.duplicate_ignored",
                extra={"challenge_id": chal.challenge_id},
            )
            return

        if existing is None:
            existing = MQTTChallenge(
                challenge_id=chal.challenge_id,
                candidate_id=settings.mqtt_candidate_id,
                status="RECEIVED",
            )
            db.add(existing)
            db.commit()
            db.refresh(existing)
        record_id = existing.id

    response = build_challenge_response(
        challenge_id=chal.challenge_id,
        candidate_id=settings.mqtt_candidate_id,
    )
    client.publish(settings.mqtt_response_topic, response)

    with SessionLocal() as db:
        record = (
            db.query(MQTTChallenge)
            .filter(MQTTChallenge.id == record_id)
            .one_or_none()
        )
        if record is not None:
            record.status = "RESPONDED"
            record.responded_at = datetime.now(timezone.utc)
            db.commit()

    logger.info(
        "mqtt.challenge.responded",
        extra={"challenge_id": chal.challenge_id},
    )


def handle_event(client: MQTTClient, payload: dict) -> None:
    """Feed MQTT events through the shared events pipeline, then publish outcome."""
    raw = payload if isinstance(payload, list) else [payload]

    try:
        events = [EventIn.model_validate(e) for e in raw]
    except Exception as exc:
        logger.error("mqtt.event.invalid", extra={"error": str(exc)})
        return

    results = []
    with SessionLocal() as db:
        try:
            results = process_batch(db, events)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("mqtt.event.commit_failed")
            for e in events:
                client.publish(
                    settings.mqtt_response_topic,
                    build_event_failure_response(e.event_id, "INTERNAL_ERROR"),
                )
            return

    for r in results:
        if r.status == "ACCEPTED" or r.status == "DUPLICATE":
            client.publish(
                settings.mqtt_response_topic,
                build_event_success_response(r.event_id, "COMPLETED"),
            )
        else:
            client.publish(
                settings.mqtt_response_topic,
                build_event_failure_response(
                    r.event_id,
                    r.error_code or r.status,
                    message=r.message,
                ),
            )

    logger.info(
        "mqtt.events.processed",
        extra={
            "count": len(results),
            "statuses": [r.status for r in results],
        },
    )
