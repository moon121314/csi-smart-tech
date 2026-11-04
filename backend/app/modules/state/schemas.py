"""Pydantic response schemas for the state module."""

from pydantic import BaseModel


class StateResponse(BaseModel):
    """Full production-state payload."""

    net_total: int
    processed_events: int
    pending_ack: int
    unresolved: int
    duplicates: int
    conflicts: int


class StateSummaryResponse(BaseModel):
    """Lightweight summary payload (view=summary)."""

    net_total: int
    pending_ack: int
    processed_events: int
