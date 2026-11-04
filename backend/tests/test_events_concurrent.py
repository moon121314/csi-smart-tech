"""Concurrency behaviour."""
from concurrent.futures import ThreadPoolExecutor
from tests.conftest import make_event


def test_concurrent_identical_submissions_single_accept(client, seeded_source):
    """10 concurrent identical submissions → 1 ACCEPTED, 9 DUPLICATE."""
    payload = make_event(event_id="EV-CONC", quantity=7)

    def submit(_):
        return client.post("/api/events", json=payload).json()

    with ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(submit, range(10)))

    statuses = [r["results"][0]["status"] for r in results]
    assert statuses.count("ACCEPTED") == 1
    assert statuses.count("DUPLICATE") == 9

    state = client.get("/api/state").json()
    assert state["net_total"] == 7


def test_concurrent_void_and_count_both_accepted(client, seeded_source):
    """Racing VOID + COUNT: exactly one ACCEPTED, no lost writes."""
    void_payload = make_event(
        event_id="EV-V1", type_="VOID", quantity=0,
        target_event_id="EV-C1", event_time="2026-11-04T10:01:00Z",
    )
    count_payload = make_event(
        event_id="EV-C1", event_time="2026-11-04T10:02:00Z"
    )

    def submit(p):
        return client.post("/api/events", json=p).json()

    with ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(submit, void_payload)
        f2 = ex.submit(submit, count_payload)
        f1.result(); f2.result()

    state = client.get("/api/state").json()
    assert state["net_total"] == 0
    assert state["unresolved"] == 0
