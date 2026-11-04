"""Application configuration, loaded from environment / .env file."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# This file lives at  backend/app/core/config.py.
# Four .parent hops reach the project root (where .env lives).
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """Typed application settings. Any missing required field fails fast at import."""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "CSI Smart Tech"
    app_version: str = "0.1.0"
    app_env: str = "development"
    log_level: str = "INFO"

    # --- Database ---
    postgres_user: str = "csi"
    postgres_password: str = "csi_dev_password"
    postgres_db: str = "csi_dashboard"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    # No defaults — must come from .env. Missing values raise on import.
    database_url: str
    test_database_url: str

    # --- MQTT ---
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_candidate_id: str = "candidate-dev"
    mqtt_enabled: bool = False

    # --- Derived MQTT topics ---
    @property
    def mqtt_challenge_topic(self) -> str:
        return f"iso-01/{self.mqtt_candidate_id}/challenge"

    @property
    def mqtt_events_topic(self) -> str:
        return f"iso-01/{self.mqtt_candidate_id}/events"

    @property
    def mqtt_response_topic(self) -> str:
        return f"iso-01/{self.mqtt_candidate_id}/responses"


# Singleton instance used across the app.
settings = Settings()
