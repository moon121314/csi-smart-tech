"""GET /api/mqtt/status endpoint for the dashboard."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.config import settings
from ...core.database import get_db
from .models import MQTTChallenge
from .schemas import MQTTStatusResponse
from .worker import MQTTWorker

router = APIRouter(prefix="/mqtt", tags=["mqtt"])

_worker: MQTTWorker | None = None


def attach_worker(worker: MQTTWorker | None) -> None:
    """Called from main.py lifespan to expose the live worker to this router."""
    global _worker
    _worker = worker


def _client_status() -> dict:
    if _worker is not None:
        return _worker.status()
    return {
        "connected": False,
        "last_message_at": None,
        "last_message_topic": None,
        "last_error": None,
    }


@router.get("/status", response_model=MQTTStatusResponse)
def mqtt_status(db: Session = Depends(get_db)) -> MQTTStatusResponse:
    cs = _client_status()

    received = int(db.scalar(select(func.count(MQTTChallenge.id))) or 0)
    responded = int(
        db.scalar(
            select(func.count(MQTTChallenge.id)).where(
                MQTTChallenge.status == "RESPONDED"
            )
        )
        or 0
    )

    def _dt(v):
        if v is None:
            return None
        return datetime.fromtimestamp(v, tz=timezone.utc)

    return MQTTStatusResponse(
        enabled=settings.mqtt_enabled,
        connected=bool(cs.get("connected")),
        candidate_id=settings.mqtt_candidate_id,
        broker_host=settings.mqtt_broker_host,
        broker_port=settings.mqtt_broker_port,
        challenge_topic=settings.mqtt_challenge_topic,
        events_topic=settings.mqtt_events_topic,
        response_topic=settings.mqtt_response_topic,
        last_message_at=_dt(cs.get("last_message_at")),
        last_message_topic=cs.get("last_message_topic"),
        last_error=cs.get("last_error"),
        challenges_received=received,
        challenges_responded=responded,
    )
