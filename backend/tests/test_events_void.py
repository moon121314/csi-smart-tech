"""VOID and PENDING_REFERENCE behaviour."""
from tests.conftest import make_event


def test_direct_void_of_accepted_count(client, seeded_source):
    client.post("/api/events", json=make_event(event_id="EV-C1"))
    r = client.post("/api/events", json=make_event(
        event_id="EV-V1", type_="VOID", quantity=0,
        target_event_id="EV-C1", event_time="2026-11-04T10:01:00Z"
    )).json()["results"][0]
    assert r["status"] == "ACCEPTED"


def test_void_before_count_is_pending(client, seeded_source):
    r = client.post("/api/events", json=make_event(
        event_id="EV-V1", type_="VOID", quantity=0,
        target_event_id="EV-C1", event_time="2026-11-04T10:01:00Z"
    )).json()["results"][0]
    assert r["status"] == "PENDING_REFERENCE"


def test_count_auto_resolves_pending_void(client, seeded_source):
    client.post("/api/events", json=make_event(
        event_id="EV-V1", type_="VOID", quantity=0,
        target_event_id="EV-C1", event_time="2026-11-04T10:01:00Z"
    ))
    r = client.post("/api/events", json=make_event(event_id="EV-C1"))
    body = r.json()["results"][0]
    assert body["status"] == "ACCEPTED"
    assert "VOID resolved" in body["message"]

    state = client.get("/api/state").json()
    assert state["net_total"] == 0


def test_void_of_voided_count_rejected(client, seeded_source):
    client.post("/api/events", json=make_event(event_id="EV-C1"))
    client.post("/api/events", json=make_event(
        event_id="EV-V1", type_="VOID", quantity=0,
        target_event_id="EV-C1", event_time="2026-11-04T10:01:00Z"
    ))
    r = client.post("/api/events", json=make_event(
        event_id="EV-V2", type_="VOID", quantity=0,
        target_event_id="EV-C1", event_time="2026-11-04T10:02:00Z"
    )).json()["results"][0]
    assert r["status"] == "REJECTED"
    assert r["error_code"] == "TARGET_NOT_VOIDABLE"


def test_void_of_void_rejected(client, seeded_source):
    client.post("/api/events", json=make_event(
        event_id="EV-V1", type_="VOID", quantity=0,
        target_event_id="EV-C1", event_time="2026-11-04T10:01:00Z"
    ))
    r = client.post("/api/events", json=make_event(
        event_id="EV-V2", type_="VOID", quantity=0,
        target_event_id="EV-V1", event_time="2026-11-04T10:02:00Z"
    )).json()["results"][0]
    assert r["status"] == "REJECTED"
    assert r["error_code"] == "INVALID_TARGET_TYPE"


def test_void_missing_target_rejected(client, seeded_source):
    r = client.post("/api/events", json=make_event(
        event_id="EV-V1", type_="VOID", quantity=0,
        target_event_id=None, event_time="2026-11-04T10:01:00Z"
    )).json()["results"][0]
    assert r["status"] == "REJECTED"
    assert r["error_code"] == "MISSING_TARGET"


def test_void_self_reference_rejected(client, seeded_source):
    r = client.post("/api/events", json=make_event(
        event_id="EV-V1", type_="VOID", quantity=0,
        target_event_id="EV-V1", event_time="2026-11-04T10:01:00Z"
    )).json()["results"][0]
    assert r["status"] == "REJECTED"
    assert r["error_code"] == "SELF_REFERENCE_TARGET"
