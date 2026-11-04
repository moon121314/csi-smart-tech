"""Aggregator: importing this module registers every ORM model with Base."""

from .core.db_base import Base
from .modules.ack.models import Acknowledgement
from .modules.events.models import ProductionEvent, SubmissionAttempt
from .modules.mqtt.models import MQTTChallenge
from .modules.sources.models import ProductionSource

__all__ = [
    "Base",
    "ProductionSource",
    "ProductionEvent",
    "SubmissionAttempt",
    "Acknowledgement",
    "MQTTChallenge",
]
