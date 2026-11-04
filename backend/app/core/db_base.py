"""Shared declarative base. Every ORM model inherits from `Base`."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all CSI Smart Tech ORM models."""

    pass
