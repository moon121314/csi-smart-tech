"""Batch processing behaviour."""
from tests.conftest import make_event


def test_batch_preserves_order_and_isolates_failures(client, seeded_source):
    events = [
        make_event(event_id="EV-1"),
        make_event(event_id="EV-2", source_id="LINE-99"),
        make_event(event_id="EV-3"),
    ]
    r = client.post("/api/events", json=events).json()["results"]
    assert len(r) == 3
    assert r[0]["event_id"] == "EV-1" and r[0]["status"] == "ACCEPTED"
    assert r[1]["event_id"] == "EV-2" and r[1]["status"] == "REJECTED"
    assert r[2]["event_id"] == "EV-3" and r[2]["status"] == "ACCEPTED"


def test_empty_batch_returns_empty_results(client):
    r = client.post("/api/events", json=[])
    assert r.status_code == 200
    assert r.json() == {"results": []}


def test_batch_with_duplicate_in_same_request(client, seeded_source):
    dup = make_event(event_id="EV-DUP")
    r = client.post("/api/events", json=[dup, dup]).json()["results"]
    assert r[0]["status"] == "ACCEPTED"
    assert r[1]["status"] == "DUPLICATE"


def test_batch_void_before_count_resolves_within_batch(client, seeded_source):
    events = [
        make_event(
            event_id="EV-V1", type_="VOID", quantity=0,
            target_event_id="EV-C1", event_time="2026-11-04T10:01:00Z",
        ),
        make_event(event_id="EV-C1"),
    ]
    r = client.post("/api/events", json=events).json()["results"]
    assert r[0]["status"] == "PENDING_REFERENCE"
    assert r[1]["status"] == "ACCEPTED"
    assert "VOID resolved" in r[1]["message"]

    state = client.get("/api/state").json()
    assert state["net_total"] == 0
