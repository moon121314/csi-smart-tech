"""POST /api/ack behaviour."""
from tests.conftest import make_event


def test_ack_success(client, seeded_source):
    client.post("/api/events", json=make_event(event_id="EV-1"))
    r = client.post("/api/ack", json={
        "event_ids": ["EV-1"], "acknowledged_by": "SUP-01"
    }).json()["results"][0]
    assert r["status"] == "ACKNOWLEDGED"


def test_ack_idempotent(client, seeded_source):
    client.post("/api/events", json=make_event(event_id="EV-1"))
    client.post("/api/ack", json={
        "event_ids": ["EV-1"], "acknowledged_by": "SUP-01"
    })
    r = client.post("/api/ack", json={
        "event_ids": ["EV-1"], "acknowledged_by": "SUP-01"
    }).json()["results"][0]
    assert r["status"] == "ALREADY_ACKNOWLEDGED"


def test_ack_unknown_event(client, seeded_source):
    r = client.post("/api/ack", json={
        "event_ids": ["EV-NOPE"], "acknowledged_by": "SUP-01"
    }).json()["results"][0]
    assert r["status"] == "NOT_FOUND"


def test_ack_voided_event_not_eligible(client, seeded_source):
    client.post("/api/events", json=make_event(event_id="EV-1"))
    client.post("/api/events", json=make_event(
        event_id="EV-V1", type_="VOID", quantity=0,
        target_event_id="EV-1", event_time="2026-11-04T10:01:00Z"
    ))
    r = client.post("/api/ack", json={
        "event_ids": ["EV-1"], "acknowledged_by": "SUP-01"
    }).json()["results"][0]
    assert r["status"] == "NOT_ELIGIBLE"


def test_ack_multi(client, seeded_source):
    for eid in ("EV-1", "EV-2", "EV-3"):
        client.post("/api/events", json=make_event(event_id=eid))
    r = client.post("/api/ack", json={
        "event_ids": ["EV-1", "EV-2", "EV-3"], "acknowledged_by": "SUP-01"
    }).json()["results"]
    assert len(r) == 3
    assert all(x["status"] == "ACKNOWLEDGED" for x in r)

    state = client.get("/api/state").json()
    assert state["pending_ack"] == 0
