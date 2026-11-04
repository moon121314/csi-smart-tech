"""Acknowledgement ORM model."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from ...core.db_base import Base


class Acknowledgement(Base):
    """A supervisor's acknowledgement of a production event.

    The UNIQUE(event_id) constraint is the idempotency guarantee:
    repeated ack requests hit the constraint and cannot double-insert.
    """

    __tablename__ = "acknowledgements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("production_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    acknowledged_by: Mapped[str] = mapped_column(String(255), nullable=False)
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="ACKNOWLEDGED"
    )

    __table_args__ = (UniqueConstraint("event_id", name="uq_acknowledgements_event"),)

    def __repr__(self) -> str:
        return (
            f"<Acknowledgement event_id={self.event_id} "
            f"by={self.acknowledged_by!r}>"
        )
