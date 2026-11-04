# CSI Smart Tech — Production Event Dashboard + MQTT Integration

A production-oriented event processing system for garment factory counting machines.
Reliably handles production `COUNT` events, reversal `VOID` events, duplicate submissions,
conflicting event IDs, out-of-order events, pending references, and supervisor
acknowledgements — with real-time production state, full audit history, MQTT device
communication, and a responsive React dashboard.

**Backend:** Python 3.12+ · FastAPI · Pydantic v2 · SQLAlchemy 2.0 · Alembic · PostgreSQL 16 · Paho MQTT
**Frontend:** React 18 · Vite 5 · plain CSS
**Infrastructure:** Docker · Docker Compose · Eclipse Mosquitto 2.0.21

---

## Table of contents

1. [Architecture](#architecture)
2. [Prerequisites](#prerequisites)
3. [Quick start](#quick-start)
4. [Environment variables](#environment-variables)
5. [API endpoints](#api-endpoints)
6. [MQTT integration](#mqtt-integration)
7. [Automated tests](#automated-tests)
8. [Project layout](#project-layout)
9. [Technology stack](#technology-stack)
10. [Troubleshooting](#troubleshooting)

---

## Architecture

**Modular monolith.** One FastAPI application, one PostgreSQL database, one MQTT worker,
one React SPA. REST and MQTT share the **same event-processing service** — one pipeline,
no duplication.

```
┌─────────────┐         ┌─────────────┐
│  REST API   │         │ MQTT worker │
│  /api/...   │         │  (paho)     │
└──────┬──────┘         └──────┬──────┘
       │                       │
       └──────────┬────────────┘
                  │
         ┌────────▼─────────┐
         │ events.service   │
         │  .process_batch  │
         └────────┬─────────┘
                  │
       ┌──────────┼──────────┐
       ▼          ▼          ▼
   repository  repository  repository
       │          │          │
       └──────────┼──────────┘
                  ▼
           ┌──────────────┐
           │  PostgreSQL  │
           └──────────────┘
```

**Key invariants enforced at the database layer:**
- `UNIQUE (source_id, event_id)` → prevents duplicate counting under concurrency
- `CHECK` on `event_type`, `quantity > 0`, `status IN (...)` → business rules can't be bypassed
- `FOREIGN KEY ... ON DELETE RESTRICT` → audit trail is immutable
- `UNIQUE (event_id)` on `acknowledgements` → idempotent supervisor ack
- `UNIQUE (challenge_id)` on `mqtt_challenges` → idempotent MQTT challenge handling

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12+ | `python3 --version` |
| Node.js | 20+ | `node --version` |
| npm | 10+ | `npm --version` |
| Docker Desktop | 24+ | Must be **running** |
| Docker Compose | v2 | `docker compose version` |

macOS users: install Python via `brew install python@3.12` if needed.

---

## Quick start

From the project root:

### 1. Clone and enter

```bash
git clone https://github.com/moon121314/csi-smart-tech.git
cd csi-smart-tech
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` if you want different database credentials. Defaults work for local dev.

### 3. Start PostgreSQL + Mosquitto

```bash
docker compose up -d
docker compose ps
```

Wait for `csi-postgres ... (healthy)` and `csi-mosquitto ... Up`.

### 4. Create the test database

```bash
docker compose exec postgres psql -U csi -d postgres -c "CREATE DATABASE csi_dashboard_test OWNER csi;"
```

(One-time only. If it errors with "already exists", skip.)

### 5. Set up backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

### 6. Seed production sources

```bash
docker compose exec postgres psql -U csi -d csi_dashboard -P pager=off -c "
INSERT INTO production_sources (source_id, name) VALUES
  ('LINE-01', 'Line 01'),
  ('LINE-02', 'Line 02')
ON CONFLICT (source_id) DO NOTHING;
"
```

### 7. Run backend

In **Terminal 1** (keep running):

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Wait for `Application startup complete`.

Verify:

```bash
curl -s http://127.0.0.1:8000/health
# → {"status":"ok","db":"ok","version":"0.1.0"}
```

### 8. Run frontend

In **Terminal 2** (keep running):

```bash
cd frontend
npm install
npm run dev
```

Wait for `Local: http://localhost:5173/`.

Open **http://localhost:5173**.

### 9. Seed demo data (optional)

In **Terminal 3**:

```bash
cd backend
source .venv/bin/activate
python3 << 'PY'
import httpx
URL = "http://127.0.0.1:8000/api/events"
events = [
    {"source_id":"LINE-01","event_id":"EV-1","type":"COUNT","quantity":5,
     "target_event_id":None,"event_time":"2026-11-04T10:00:00Z"},
    {"source_id":"LINE-01","event_id":"EV-2","type":"COUNT","quantity":10,
     "target_event_id":None,"event_time":"2026-11-04T10:01:00Z"},
    {"source_id":"LINE-02","event_id":"EV-3","type":"COUNT","quantity":20,
     "target_event_id":None,"event_time":"2026-11-04T10:02:00Z"},
    {"source_id":"LINE-01","event_id":"EV-V1","type":"VOID","quantity":0,
     "target_event_id":"EV-1","event_time":"2026-11-04T10:03:00Z"},
]
for r in httpx.post(URL, json=events).json()["results"]:
    print(f"  {r['event_id']}: {r['status']}")
PY
```

Refresh the browser. Cards will show:
- Net Total = 30 (5 was voided, so 10+20 remain)
- Processed = 3
- Pending Ack = 2

---

## Environment variables

All required values in `.env` (root):

| Variable | Default | Purpose |
|---|---|---|
| `POSTGRES_USER` | `csi` | Postgres username |
| `POSTGRES_PASSWORD` | `csi_dev_password` | Postgres password |
| `POSTGRES_DB` | `csi_dashboard` | App database name |
| `POSTGRES_HOST` | `localhost` | Postgres host |
| `POSTGRES_PORT` | `5432` | Postgres port (host-side) |
| `DATABASE_URL` | `postgresql+psycopg://...` | Full SQLAlchemy URL |
| `TEST_DATABASE_URL` | `postgresql+psycopg://...` | Test DB URL |
| `APP_ENV` | `development` | Environment name (for logging) |
| `LOG_LEVEL` | `INFO` | Python log level |
| `MQTT_ENABLED` | `false` | Enable MQTT worker at startup |
| `MQTT_BROKER_HOST` | `localhost` | MQTT broker host |
| `MQTT_BROKER_PORT` | `1883` | MQTT broker port |
| `MQTT_CANDIDATE_ID` | `candidate-dev` | Topic namespace segment |

**Never commit `.env`** — it's gitignored. Only `.env.example` is committed.

**To enable MQTT:** set `MQTT_ENABLED=true` in `.env`, restart uvicorn.

---

## API endpoints

Full interactive docs at **http://127.0.0.1:8000/docs** (Swagger UI).

### `POST /api/events`

Accepts a single event or an array. Returns one result per event, in submission order.

**Valid COUNT request:**
```json
{
  "source_id": "LINE-01",
  "event_id": "EV-101",
  "type": "COUNT",
  "quantity": 5,
  "target_event_id": null,
  "event_time": "2026-11-04T10:00:00Z"
}
```

**Response:**
```json
{
  "results": [
    {
      "event_id": "EV-101",
      "status": "ACCEPTED",
      "message": "Production count accepted"
    }
  ]
}
```

**VOID request (reverse an accepted COUNT):**
```json
{
  "source_id": "LINE-01",
  "event_id": "EV-V1",
  "type": "VOID",
  "quantity": 0,
  "target_event_id": "EV-101",
  "event_time": "2026-11-04T10:05:00Z"
}
```

**VOID before COUNT (arrives first):**
- First submission returns `PENDING_REFERENCE`
- When the matching COUNT arrives, the VOID is auto-resolved
- Both events end up `ACCEPTED`; net total updates correctly

**Status values returned:**

| Status | Meaning |
|---|---|
| `ACCEPTED` | Event persisted and applied |
| `DUPLICATE` | Same (source_id, event_id) and identical payload |
| `CONFLICT` | Same (source_id, event_id) but different payload |
| `PENDING_REFERENCE` | VOID stored, waiting for its target COUNT |
| `REJECTED` | Validation failure (see `error_code`) |

### `GET /api/state`

Optional query params:
- `source_id=LINE-01` — filter to one source
- `view=summary` — lighter 3-field response

**Response:**
```json
{
  "net_total": 33,
  "processed_events": 5,
  "pending_ack": 4,
  "unresolved": 1,
  "duplicates": 0,
  "conflicts": 0
}
```

Field meanings:
- `net_total` — sum of accepted COUNT quantities (voided COUNTs excluded)
- `processed_events` — events settled to ACCEPTED or VOIDED
- `pending_ack` — ACCEPTED events with no acknowledgement row
- `unresolved` — events stuck in PENDING_REFERENCE (missing target)
- `duplicates` — submission attempts that returned DUPLICATE
- `conflicts` — submission attempts that returned CONFLICT

### `POST /api/ack`

**Request:**
```json
{
  "event_ids": ["EV-101", "EV-102"],
  "acknowledged_by": "SUP-01"
}
```

**Response:**
```json
{
  "results": [
    {"event_id": "EV-101", "status": "ACKNOWLEDGED", "message": "..."},
    {"event_id": "EV-102", "status": "ALREADY_ACKNOWLEDGED", "message": "..."}
  ]
}
```

Status values: `ACKNOWLEDGED`, `ALREADY_ACKNOWLEDGED` (idempotent), `NOT_FOUND`, `NOT_ELIGIBLE` (VOIDED or PENDING_REFERENCE), `AMBIGUOUS_EVENT_ID`, `ERROR`.

### `GET /api/events`

Not required by the assessment — added to support the dashboard listing.
Query params: `limit` (1–500, default 50), `status`, `include_voided` (bool).

### `GET /api/mqtt/status`

Live MQTT connection state for the dashboard widget.

### `GET /health`

Liveness + DB reachability probe.

---

## MQTT integration

### Topics (with `candidate_id` from `.env`)

| Direction | Topic |
|---|---|
| Subscribe | `iso-01/{candidate_id}/challenge` |
| Subscribe | `iso-01/{candidate_id}/events` |
| Publish | `iso-01/{candidate_id}/responses` |

### Behavior

- **Challenge**: durable row in `mqtt_challenges` with `UNIQUE(challenge_id)`.
  Duplicate challenges do **not** trigger a second response.
- **Events**: full JSON payload fed through the same `process_batch` as REST.
  Response published **only after DB commit**.
  Accepted events → `{"event_id": "...", "status": "COMPLETED"}`.
  Rejected/conflict → `{"event_id": "...", "status": "FAILURE", "error_code": "..."}`.

### Wire-format customization

If the assessment spec (Q3/Q4) requires a different response shape, edit **only this file**:

`backend/app/modules/mqtt/wire_format.py`

Then restart uvicorn. No other code changes.

### Local broker test

```bash
cd backend
source .venv/bin/activate
python3 << 'PY'
import json, time
import paho.mqtt.client as mqtt

CAND = "candidate-dev"
received = []
def on_message(client, userdata, msg):
    received.append((msg.topic, json.loads(msg.payload)))

sub = mqtt.Client(client_id="test-sub")
sub.on_message = on_message
sub.connect("localhost", 1883, 60)
sub.subscribe(f"iso-01/{CAND}/responses", qos=1)
sub.loop_start()
time.sleep(0.5)

pub = mqtt.Client(client_id="test-pub")
pub.connect("localhost", 1883, 60)
pub.loop_start()

pub.publish(f"iso-01/{CAND}/challenge", json.dumps({"challenge_id": "CH-001"}), qos=1)
time.sleep(1)

pub.publish(f"iso-01/{CAND}/events", json.dumps({
    "source_id": "LINE-01", "event_id": "EV-MQTT-1", "type": "COUNT",
    "quantity": 3, "target_event_id": None,
    "event_time": "2026-11-04T16:00:00Z",
}), qos=1)
time.sleep(2)

sub.loop_stop(); pub.loop_stop()
print(f"\nReceived {len(received)} responses:")
for topic, payload in received:
    print(f"  {topic}: {payload}")
PY
```

**Expected:** 2 responses — one challenge echo, one `COMPLETED` event ack.

---

## Automated tests

```bash
cd backend
source .venv/bin/activate
pytest -v
```

**Expected:** **27 passed** against real PostgreSQL test database.

| Test file | Coverage |
|---|---|
| `test_events_count.py` | Valid COUNT, invalid quantity, unknown source, duplicate, conflict |
| `test_events_void.py` | Direct VOID, pending VOID, auto-resolution, void-of-void, void-of-voided |
| `test_events_batch.py` | Per-event savepoint isolation, empty batch, in-batch VOID+COUNT |
| `test_events_concurrent.py` | 10 concurrent identical submissions; concurrent VOID+COUNT |
| `test_ack.py` | Ack, idempotency, unknown event, not-eligible, multi-ack |
| `test_state.py` | Global, per-source, summary view |

Tests use `TEST_DATABASE_URL` — production DB is **never touched**.

---

## Project layout

```
csi-smart-tech/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app factory + lifespan (MQTT start/stop)
│   │   ├── models.py                  # Aggregator for Alembic autogenerate
│   │   ├── core/
│   │   │   ├── config.py              # Pydantic Settings
│   │   │   ├── database.py            # SQLAlchemy engine + session factory
│   │   │   ├── db_base.py             # Declarative Base
│   │   │   └── logging.py             # Structured JSON logger
│   │   ├── modules/
│   │   │   ├── events/                # Event CRUD, VOID, pending resolution
│   │   │   ├── ack/                   # Supervisor acknowledgements
│   │   │   ├── state/                 # Aggregate queries
│   │   │   ├── mqtt/                  # Paho client, worker, wire format
│   │   │   ├── sources/               # Production sources
│   │   │   ├── audit/                 # (reserved for extension)
│   │   │   └── common/                # Enums, base exceptions
│   │   └── migrations/                # Alembic env + versions
│   ├── tests/                         # pytest suite
│   ├── alembic.ini
│   ├── requirements.txt
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── components/                # SummaryCards, EventTable, MQTTStatus, ...
│   │   ├── pages/Dashboard.jsx
│   │   ├── services/api.js
│   │   ├── hooks/usePolling.js
│   │   ├── styles/app.css
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── mosquitto/
│   └── mosquitto.conf
├── docs/
│   └── demo_guide.md
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── TECHNICAL_EXPLANATION.md
├── REQUIREMENT_DECISIONS.md
└── AI_USAGE.md
```

---

## Technology stack

### Backend
- Python 3.12+
- FastAPI 0.115+
- Pydantic v2 + pydantic-settings
- SQLAlchemy 2.0
- Alembic (migrations)
- PostgreSQL 16 (Alpine)
- psycopg 3 (driver)
- Paho MQTT 2.1
- Uvicorn (ASGI)

### Frontend
- React 18.3
- Vite 5.4
- JavaScript (JSX)
- Fetch API
- Plain CSS + responsive media queries

### Infrastructure
- Docker
- Docker Compose v2
- Eclipse Mosquitto 2.0.21

### Testing
- Pytest 8+
- pytest-asyncio
- HTTPX
- FastAPI TestClient

### Database schema
- `production_sources`
- `production_events` (UNIQUE `source_id` + `event_id`)
- `submission_attempts` (JSONB payload, full audit)
- `acknowledgements` (UNIQUE `event_id`)
- `mqtt_challenges` (UNIQUE `challenge_id`)
- `alembic_version`

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `docker compose ps` shows Postgres `unhealthy` | `docker compose logs postgres` — usually corrupted volume. `docker compose down -v && docker compose up -d` (wipes DB) |
| uvicorn: `Address already in use` on 8000 | `lsof -ti:8000 \| xargs kill -9` then restart |
| uvicorn: `psycopg.OperationalError` | Postgres not up. `docker compose ps` → start if needed |
| `pydantic_core.ValidationError: database_url Field required` | `.env` missing or wrong path. Verify `ls -la .env` from project root |
| Frontend: blank page | Check Terminal 2 for compile errors. Hard-refresh browser (Cmd+Shift+R) |
| Frontend: `Failed to fetch` in console | Backend not running — start Terminal 1 |
| Frontend: proxy 404 on `/api/...` | Check `vite.config.js` has `proxy: { '/api': 'http://127.0.0.1:8000' }` |
| MQTT: `mqtt.disconnected rc=7` | Mosquitto not on 1883. `docker compose logs mosquitto` — must show `Opening ipv4 listen socket on port 1883` |
| MQTT: `'str' object has no attribute 'publish'` | Outdated `client.py`. Ensure `handler(self, payload)` not `handler(topic, payload)` |
| `alembic upgrade head` fails on FK | `alembic downgrade base` then `upgrade head` |
| `pytest` cannot find DB | `TEST_DATABASE_URL` wrong or test DB missing. `docker compose exec postgres psql -U csi -d postgres -c "CREATE DATABASE csi_dashboard_test OWNER csi;"` |
