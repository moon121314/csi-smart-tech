"""Domain enumerations used across modules."""

from enum import StrEnum


class EventType(StrEnum):
    COUNT = "COUNT"
    VOID = "VOID"


class EventStatus(StrEnum):
    """State of a ProductionEvent row."""

    ACCEPTED = "ACCEPTED"
    VOIDED = "VOIDED"
    PENDING_REFERENCE = "PENDING_REFERENCE"


class SubmissionResult(StrEnum):
    """What we return to the caller for each submission."""

    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    PENDING_REFERENCE = "PENDING_REFERENCE"
    REJECTED = "REJECTED"


class AckStatus(StrEnum):
    ACKNOWLEDGED = "ACKNOWLEDGED"


class MQTTChallengeStatus(StrEnum):
    RECEIVED = "RECEIVED"
    RESPONDED = "RESPONDED"
    FAILED = "FAILED"
