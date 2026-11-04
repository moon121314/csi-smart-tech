"""Pydantic schemas for incoming MQTT payloads and status reporting."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ChallengePayload(BaseModel):
    """Incoming challenge. Minimum required: challenge_id. Extras preserved."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    challenge_id: str = Field(..., min_length=1, max_length=255)

    def raw(self) -> dict[str, Any]:
        return self.model_dump()


class MQTTStatusResponse(BaseModel):
    """Dashboard-friendly connection status."""

    enabled: bool
    connected: bool
    candidate_id: str
    broker_host: str
    broker_port: int
    challenge_topic: str
    events_topic: str
    response_topic: str
    last_message_at: datetime | None = None
    last_message_topic: str | None = None
    last_error: str | None = None
    challenges_received: int = 0
    challenges_responded: int = 0
