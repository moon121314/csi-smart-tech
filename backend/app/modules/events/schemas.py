"""Pydantic schemas for the events module."""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventIn(BaseModel):
    """Incoming event, as submitted by a device or supervisor."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    source_id: str = Field(..., min_length=1, max_length=64)
    event_id: str = Field(..., min_length=1, max_length=64)
    type: str
    quantity: int
    target_event_id: str | None = Field(default=None, max_length=64)
    event_time: datetime

    @field_validator("event_time")
    @classmethod
    def ensure_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)


class EventResult(BaseModel):
    """Per-event outcome returned in the batch response."""

    event_id: str
    status: str
    message: str
    error_code: str | None = None


class BatchResponse(BaseModel):
    results: list[EventResult]


class EventOut(BaseModel):
    """Serialized ProductionEvent for the dashboard listing."""

    id: int
    source_id: str
    event_id: str
    event_type: str
    quantity: int
    target_event_id: str | None
    event_time: datetime
    status: str
    created_at: datetime
    acknowledged: bool
    acknowledged_by: str | None


class EventListResponse(BaseModel):
    events: list[EventOut]
