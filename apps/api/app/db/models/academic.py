from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, SoftDeleteMixin, TimestampMixin, guid, guid_pk


class Department(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "departments"

    id: Mapped[object] = guid_pk()
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    semesters = relationship("Semester", back_populates="department", cascade="all, delete-orphan")
    sections = relationship("Section", back_populates="department", cascade="all, delete-orphan")


class Semester(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "semesters"

    id: Mapped[object] = guid_pk()
    department_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("departments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    ordinal: Mapped[int] = mapped_column(nullable=False)  # 1, 2, 3, ...
    academic_year: Mapped[str | None] = mapped_column(String(20), nullable=True)

    department = relationship("Department", back_populates="semesters")


class Section(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sections"

    id: Mapped[object] = guid_pk()
    department_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("departments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    semester_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("semesters.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)

    department = relationship("Department", back_populates="sections")
    semester = relationship("Semester")
