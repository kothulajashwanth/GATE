from enum import StrEnum

from sqlalchemy import Boolean, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, SoftDeleteMixin, TimestampMixin, guid_pk


class Role(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    STUDENT = "student"
    FACULTY = "faculty"


class User(Base, TimestampMixin, SoftDeleteMixin):
    """A platform account. For students this maps 1:1 to a Student profile."""

    __tablename__ = "users"

    id: Mapped[object] = guid_pk()
    clerk_id: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, name="user_role"), default=Role.STUDENT, index=True, nullable=False
    )
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    student = relationship("Student", back_populates="user", uselist=False)

    @property
    def full_name(self) -> str:
        parts = [p for p in (self.first_name, self.last_name) if p]
        return " ".join(parts) if parts else self.email

    @property
    def name(self) -> str:
        return self.full_name

    @property
    def clerk_user_id(self) -> str | None:
        return self.clerk_id

    @property
    def status(self) -> str:
        return "active" if self.is_active else "inactive"

