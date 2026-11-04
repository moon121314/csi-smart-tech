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
from .modules.ack.router import router as ack_router
from .modules.events.router import router as events_router
from .modules.mqtt.router import attach_worker
from .modules.mqtt.router import router as mqtt_router
from .modules.mqtt.worker import MQTTWorker
from .modules.state.router import router as state_router


configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "app.startup",
        extra={"env": settings.app_env, "version": settings.app_version},
    )

    worker: MQTTWorker | None = None
    if settings.mqtt_enabled:
        worker = MQTTWorker()
        worker.start()
        attach_worker(worker)
    else:
        logger.info("mqtt.disabled_by_config")

    yield

    if worker is not None:
        worker.stop()
        attach_worker(None)
    logger.info("app.shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def request_validation_handler(request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": "Invalid request structure", "errors": exc.errors()},
    )


@app.get("/health")
def health():
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
app.include_router(state_router, prefix="/api")
app.include_router(ack_router, prefix="/api")
app.include_router(mqtt_router, prefix="/api")
