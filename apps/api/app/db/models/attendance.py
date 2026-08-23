from datetime import date, datetime, timezone
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, SoftDeleteMixin, TimestampMixin, guid, guid_pk


class AttendanceStatus(StrEnum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"


class SessionState(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class AttendanceSession(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "attendance_sessions"

    id: Mapped[object] = guid_pk()
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_id: Mapped[object] = mapped_column(guid(), ForeignKey("subjects.id"), nullable=False, index=True)
    department_id: Mapped[object | None] = mapped_column(guid(), ForeignKey("departments.id"), nullable=True, index=True)
    semester_id: Mapped[object | None] = mapped_column(guid(), ForeignKey("semesters.id"), nullable=True, index=True)
    section_id: Mapped[object | None] = mapped_column(guid(), ForeignKey("sections.id"), nullable=True, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    start_time: Mapped[str] = mapped_column(String(10), nullable=False, default="09:00")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=SessionState.ACTIVE)
    created_by: Mapped[object] = mapped_column(guid(), ForeignKey("users.id"), nullable=False)

    subject = relationship("Subject")
    department = relationship("Department")
    semester = relationship("Semester")
    section = relationship("Section")
    creator = relationship("User")
    records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")


class AttendanceRecord(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_attendance_session_student"),
    )

    id: Mapped[object] = guid_pk()
    session_id: Mapped[object] = mapped_column(guid(), ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[object] = mapped_column(guid(), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=AttendanceStatus.PRESENT)
    remarks: Mapped[str | None] = mapped_column(String(255), nullable=True)
    marked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    session = relationship("AttendanceSession", back_populates="records")
    student = relationship("Student")
