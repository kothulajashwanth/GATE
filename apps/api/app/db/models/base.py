from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def guid() -> Any:
    """UUID primary key column: native UUID on Postgres, CHAR(32) elsewhere (tests)."""
    return Uuid(as_uuid=True)


def guid_pk(*, fk: str | None = None) -> Mapped[UUID]:
    """mapped_column fragment for a UUID PK with a client-side default.

    Pass ``fk`` to make this a foreign key column instead (no default needed).
    """
    if fk is not None:
        from sqlalchemy import ForeignKey

        return mapped_column(guid(), ForeignKey(fk, ondelete="CASCADE"))
    return mapped_column(guid(), primary_key=True, default=uuid4)


class TimestampMixin:

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SoftDeleteMixin:
    """Adds a nullable deleted_at column; soft-deleted rows are hidden by default queries."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
