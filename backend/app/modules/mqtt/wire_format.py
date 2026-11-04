"""
Wire-format payload builders for MQTT messages published BY this client.

⚠️  WHEN THE ASSESSMENT SPEC FOR Q3/Q4 ARRIVES, THIS IS THE ONLY FILE
    THAT NEEDS TO CHANGE.  Restart uvicorn afterwards — no other edits.

Q3 = exact challenge response JSON structure
Q4 = exact event acknowledgement JSON structure
"""

from typing import Any


def build_challenge_response(challenge_id: str, candidate_id: str) -> dict[str, Any]:
    """
    TODO(Q3): replace body with the exact structure required by the assessment.

    Current default (matches the most common assessment pattern):
        {"challenge_id": "<id>", "candidate_id": "<candidate_id>"}

    If the spec asks for extra fields — e.g. "response", "signature",
    "timestamp" — add them here. Only this function needs to change.
    """
    return {
        "challenge_id": challenge_id,
        "candidate_id": candidate_id,
    }


def build_event_success_response(event_id: str, status: str) -> dict[str, Any]:
    """
    TODO(Q4): replace body with the exact success response structure.

    Current default:
        {"event_id": "<id>", "status": "COMPLETED"}
    """
    return {
        "event_id": event_id,
        "status": status,
    }


def build_event_failure_response(
    event_id: str, error_code: str, message: str | None = None
) -> dict[str, Any]:
    """
    TODO(Q4): replace body with the exact failure response structure.

    Current default:
        {"event_id": "<id>", "status": "FAILURE", "error_code": "<code>"}
    """
    payload: dict[str, Any] = {
        "event_id": event_id,
        "status": "FAILURE",
        "error_code": error_code,
    }
    if message:
        payload["message"] = message
    return payload
