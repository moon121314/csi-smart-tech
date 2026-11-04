"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .core.config import settings
from .core.database import SessionLocal
from .core.logging import configure_logging
from .modules.events.router import router as events_router

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "app.startup",
        extra={"env": settings.app_env, "version": settings.app_version},
    )
    yield
    logger.info("app.shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request, exc: RequestValidationError):
    """Return 400 for malformed request structures (per API contract)."""
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid request structure", "errors": exc.errors()},
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


app.include_router(events_router, prefix="/api")
