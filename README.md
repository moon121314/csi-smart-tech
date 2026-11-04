
**Key design choices:**

1. **Background thread** — Paho is sync-blocking. Running it in the FastAPI event loop would
   block request handling. Paho's own `loop_start()` spins a dedicated thread.

2. **Shared service** — `mqtt.service.handle_event()` calls `process_batch()` from
   `events.service`. This is the assessment's "one shared event-processing service"
   requirement. REST and MQTT cannot diverge.

3. **Publish-after-commit** — the MQTT response is published only after `db.commit()` succeeds.
   A network failure during publish does not lose the DB write; the client will retry.

4. **Idempotent challenges** — `UNIQUE(challenge_id)` + status check prevents double-response.
   Even if the broker replays the challenge, we emit one response.

5. **Reconnect with backoff** — Paho's `reconnect_delay_set(min_delay=1, max_delay=60)`
   retries indefinitely.
