"""COUNT event behaviour."""
from tests.conftest import make_event


def test_valid_count_accepted(client, seeded_source):
    r = client.post("/api/events", json=make_event())
    assert r.status_code == 200
    assert r.json()["results"][0]["status"] == "ACCEPTED"


def test_invalid_quantity_rejected(client, seeded_source):
    r = client.post("/api/events", json=make_event(quantity=0))
    body = r.json()["results"][0]
    assert body["status"] == "REJECTED"
    assert body["error_code"] == "INVALID_QUANTITY"


def test_unknown_source_rejected(client, seeded_source):
    r = client.post("/api/events", json=make_event(source_id="LINE-99"))
    body = r.json()["results"][0]
    assert body["status"] == "REJECTED"
    assert body["error_code"] == "SOURCE_NOT_FOUND"


def test_duplicate_identical_content(client, seeded_source):
    payload = make_event()
    first = client.post("/api/events", json=payload).json()["results"][0]
    second = client.post("/api/events", json=payload).json()["results"][0]
    assert first["status"] == "ACCEPTED"
    assert second["status"] == "DUPLICATE"


def test_conflict_different_content(client, seeded_source):
    payload = make_event(quantity=5)
    client.post("/api/events", json=payload)
    changed = make_event(quantity=99)
    r = client.post("/api/events", json=changed).json()["results"][0]
    assert r["status"] == "CONFLICT"
    assert r["error_code"] == "CONFLICT"


def test_count_with_target_rejected(client, seeded_source):
    r = client.post(
        "/api/events", json=make_event(target_event_id="EV-OTHER")
    ).json()["results"][0]
    assert r["status"] == "REJECTED"
    assert r["error_code"] == "UNEXPECTED_TARGET"
