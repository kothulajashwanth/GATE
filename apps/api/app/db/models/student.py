from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, SoftDeleteMixin, TimestampMixin, guid, guid_pk


class Student(Base, TimestampMixin, SoftDeleteMixin):
    """Student profile, linked to a platform account and an academic placement."""

    __tablename__ = "students"

    id: Mapped[object] = guid_pk()
    user_id: Mapped[object] = mapped_column(guid(), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    roll_number: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    department_id: Mapped[object] = mapped_column(guid(), ForeignKey("departments.id"), index=True, nullable=False)
    semester_id: Mapped[object] = mapped_column(guid(), ForeignKey("semesters.id"), index=True, nullable=False)
    section_id: Mapped[object] = mapped_column(guid(), ForeignKey("sections.id"), index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    parent_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    parent_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    enrollment_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user = relationship("User", back_populates="student")
    department = relationship("Department")
    semester = relationship("Semester")
    section = relationship("Section")
