"""SQLAlchemy 2.0 engine and session factory."""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import settings

# One engine per process. `pool_pre_ping` protects against stale connections
# after Postgres restarts (frequent in Docker dev).
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=False,
    future=True,
)


# Session factory. `expire_on_commit=False` keeps ORM objects usable after
# commit without an extra SELECT — handy when services return DTOs.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yield a session, close it when the request ends."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
