"""Thread-safe Paho MQTT client wrapper with reconnect and status tracking."""

import json
import logging
import threading
import time
from typing import Any, Callable

import paho.mqtt.client as mqtt

from ...core.config import settings

logger = logging.getLogger(__name__)


class MQTTClient:
    """Owns a Paho client, tracks connection state, dispatches messages."""

    def __init__(self, client_id: str | None = None):
        cid = client_id or f"csi-{settings.mqtt_candidate_id}"
        self._client = mqtt.Client(
            client_id=cid,
            protocol=mqtt.MQTTv311,
            clean_session=True,
        )
        self._client.reconnect_delay_set(min_delay=1, max_delay=60)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

        # topic-pattern → handler(topic, payload_dict)
        self._handlers: dict[str, Callable[[str, dict], None]] = {}
        self._lock = threading.Lock()
        self._status: dict[str, Any] = {
            "connected": False,
            "candidate_id": settings.mqtt_candidate_id,
            "last_message_at": None,
            "last_message_topic": None,
            "last_error": None,
            "connected_at": None,
        }

    def register_handler(
        self, topic_pattern: str, handler: Callable[[str, dict], None]
    ) -> None:
        self._handlers[topic_pattern] = handler

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            with self._lock:
                self._status["connected"] = True
                self._status["connected_at"] = time.time()
                self._status["last_error"] = None
            logger.info("mqtt.connected", extra={"rc": rc})
            for pattern in self._handlers:
                client.subscribe(pattern, qos=1)
                logger.info("mqtt.subscribed", extra={"topic": pattern})
        else:
            logger.error("mqtt.connect_failed", extra={"rc": rc})
            with self._lock:
                self._status["last_error"] = f"connect rc={rc}"

    def _on_disconnect(self, client, userdata, rc, properties=None):
        with self._lock:
            self._status["connected"] = False
        logger.warning("mqtt.disconnected", extra={"rc": rc})

    def _on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception as exc:
            logger.error(
                "mqtt.decode_failed",
                extra={"topic": topic, "error": str(exc)},
            )
            with self._lock:
                self._status["last_error"] = f"decode: {exc}"
            return

        with self._lock:
            self._status["last_message_at"] = time.time()
            self._status["last_message_topic"] = topic

        handler = None
        for pattern, fn in self._handlers.items():
            if mqtt.topic_matches_sub(pattern, topic):
                handler = fn
                break

        if handler is None:
            logger.warning("mqtt.unhandled_topic", extra={"topic": topic})
            return

        try:
            handler(topic, payload)
        except Exception as exc:
            logger.exception(
                "mqtt.handler_error",
                extra={"topic": topic, "error": str(exc)},
            )
            with self._lock:
                self._status["last_error"] = str(exc)

    def start(self) -> None:
        try:
            self._client.connect_async(
                settings.mqtt_broker_host,
                settings.mqtt_broker_port,
                keepalive=60,
            )
            self._client.loop_start()
            logger.info(
                "mqtt.starting",
                extra={
                    "host": settings.mqtt_broker_host,
                    "port": settings.mqtt_broker_port,
                },
            )
        except Exception as exc:
            logger.exception("mqtt.start_failed", extra={"error": str(exc)})
            with self._lock:
                self._status["last_error"] = str(exc)

    def stop(self) -> None:
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:
            pass
        with self._lock:
            self._status["connected"] = False
        logger.info("mqtt.stopped")

    def publish(self, topic: str, payload: dict, qos: int = 1) -> None:
        try:
            info = self._client.publish(topic, json.dumps(payload), qos=qos)
            logger.info(
                "mqtt.published",
                extra={"topic": topic, "rc": info.rc, "mid": info.mid},
            )
        except Exception as exc:
            logger.exception(
                "mqtt.publish_failed",
                extra={"topic": topic, "error": str(exc)},
            )

    def status(self) -> dict:
        with self._lock:
            return dict(self._status)
