"""GET /api/state behaviour."""
from tests.conftest import make_event


def _seed_two_sources(client):
    client.post("/api/events", json=make_event(
        event_id="EV-L1", source_id="LINE-01", quantity=10
    ))
    client.post("/api/events", json=make_event(
        event_id="EV-L2", source_id="LINE-02", quantity=20
    ))


def test_state_global(client, seeded_source):
    _seed_two_sources(client)
    s = client.get("/api/state").json()
    assert s["net_total"] == 30
    assert s["processed_events"] == 2
    assert s["pending_ack"] == 2


def test_state_filtered_by_source(client, seeded_source):
    _seed_two_sources(client)
    s = client.get("/api/state", params={"source_id": "LINE-01"}).json()
    assert s["net_total"] == 10
    assert s["processed_events"] == 1


def test_state_summary_view(client, seeded_source):
    _seed_two_sources(client)
    s = client.get("/api/state", params={"view": "summary"}).json()
    assert set(s.keys()) == {"net_total", "pending_ack", "processed_events"}
    assert s["net_total"] == 30
