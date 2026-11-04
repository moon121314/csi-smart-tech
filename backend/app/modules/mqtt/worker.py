"""MQTT worker: owns the client lifecycle within the FastAPI app."""

import logging

from ...core.config import settings
from .client import MQTTClient
from .service import handle_challenge, handle_event

logger = logging.getLogger(__name__)


class MQTTWorker:
    """Wraps MQTTClient with topic→handler wiring for our two inbound topics."""

    def __init__(self) -> None:
        self.client = MQTTClient()
        self.client.register_handler(settings.mqtt_challenge_topic, handle_challenge)
        self.client.register_handler(settings.mqtt_events_topic, handle_event)

    def start(self) -> None:
        logger.info(
            "mqtt.worker.starting",
            extra={
                "challenge_topic": settings.mqtt_challenge_topic,
                "events_topic": settings.mqtt_events_topic,
                "response_topic": settings.mqtt_response_topic,
            },
        )
        self.client.start()

    def stop(self) -> None:
        self.client.stop()
        logger.info("mqtt.worker.stopped")

    def status(self) -> dict:
        return self.client.status()
