"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from .core.config import settings
from .core.database import SessionLocal
from .core.logging import configure_logging

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on startup and shutdown. Placeholder for MQTT worker start later."""
    logger.info(
        "app.startup", extra={"env": settings.app_env, "version": settings.app_version}
    )
    yield
    logger.info("app.shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)


@app.get("/health")
def health():
    """Liveness + database reachability probe."""
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:  # noqa: BLE001
        logger.error(f"health.db_check_failed error={exc}")
        db_status = "error"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
        "version": settings.app_version,
    }
