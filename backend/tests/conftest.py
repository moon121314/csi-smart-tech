"""Test fixtures. Real PostgreSQL, no SQLite, no mocks."""
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# IMPORT ORDER IS CRITICAL:
# `import app.models` rebinds the name `app` to the package module.
# Importing app.main.app MUST come last so the FastAPI instance wins.
import app.models  # noqa: F401 — registers all ORM models with Base.metadata

from app.core.config import settings
from app.core.db_base import Base
from app.core.database import get_db
from app.main import app  # noqa: E402 — FastAPI instance, imported last on purpose


TEST_URL = settings.test_database_url

test_engine = create_engine(TEST_URL, pool_pre_ping=True, future=True)
TestSessionLocal = sessionmaker(
    bind=test_engine, autoflush=False, expire_on_commit=False
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create schema once per test session against real PostgreSQL."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(autouse=True)
def clean_db():
    """Truncate all tables between tests."""
    with test_engine.begin() as conn:
        conn.execute(text(
            "TRUNCATE production_events, submission_attempts, "
            "acknowledgements, production_sources, mqtt_challenges "
            "RESTART IDENTITY CASCADE"
        ))
    yield


@pytest.fixture
def client():
    """TestClient with get_db overridden to test DB."""
    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seeded_source(client):
    """Seed LINE-01 and LINE-02 in the test DB."""
    db = TestSessionLocal()
    try:
        db.execute(text(
            "INSERT INTO production_sources (source_id, name) VALUES "
            "('LINE-01', 'Line 01'), ('LINE-02', 'Line 02')"
        ))
        db.commit()
    finally:
        db.close()
    return "LINE-01"


def make_event(source_id="LINE-01", event_id="EV-1", type_="COUNT",
               quantity=5, target_event_id=None,
               event_time="2026-11-04T10:00:00Z"):
    return {
        "source_id": source_id,
        "event_id": event_id,
        "type": type_,
        "quantity": quantity,
        "target_event_id": target_event_id,
        "event_time": event_time,
    }
