"""Pydantic schemas for the acknowledgement module."""

from pydantic import BaseModel, Field


class AckRequest(BaseModel):
    event_ids: list[str] = Field(..., min_length=1)
    acknowledged_by: str = Field(..., min_length=1, max_length=255)


class AckResult(BaseModel):
    event_id: str
    status: str
    message: str
    error_code: str | None = None


class AckResponse(BaseModel):
    results: list[AckResult]
