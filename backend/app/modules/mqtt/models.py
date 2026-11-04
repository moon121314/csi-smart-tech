"""MQTTChallenge ORM model — durable record of every challenge received."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db_base import Base


class MQTTChallenge(Base):
    """Persistent log of challenges received over MQTT.

    UNIQUE(challenge_id) makes challenge handling idempotent: if the broker
    re-sends the same challenge after a reconnect, we see the row already
    exists and skip responding again.
    """

    __tablename__ = "mqtt_challenges"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    challenge_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    candidate_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="RECEIVED"
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    responded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return (
            f"<MQTTChallenge challenge_id={self.challenge_id!r} "
            f"status={self.status}>"
        )
