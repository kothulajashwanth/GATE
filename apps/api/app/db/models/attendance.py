from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, SoftDeleteMixin, TimestampMixin, guid, guid_pk


class SessionState(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"


class AttendanceStatus(StrEnum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"


class AttendanceSession(Base, TimestampMixin, SoftDeleteMixin):
    """Class or lecture attendance session."""

    __tablename__ = "attendance_sessions"

    id: Mapped[object] = guid_pk()
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    subject_id: Mapped[object | None] = mapped_column(guid(), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    department_id: Mapped[object | None] = mapped_column(guid(), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    semester_id: Mapped[object | None] = mapped_column(guid(), ForeignKey("semesters.id", ondelete="SET NULL"), nullable=True)
    section_id: Mapped[object | None] = mapped_column(guid(), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[object] = mapped_column(guid(), ForeignKey("users.id"), nullable=False)
    session_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    status: Mapped[SessionState] = mapped_column(SAEnum(SessionState), default=SessionState.DRAFT, nullable=False)
    qr_secret: Mapped[str] = mapped_column(String(64), nullable=False)
    qr_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    subject = relationship("Subject")
    department = relationship("Department")
    semester = relationship("Semester")
    section = relationship("Section")
    creator = relationship("User")
    records = relationship("AttendanceRecord", back_populates="session", cascade="all, delete-orphan")


class AttendanceRecord(Base, TimestampMixin, SoftDeleteMixin):
    """Attendance record for a specific student in an attendance session."""

    __tablename__ = "attendance_records"

    __table_args__ = (
        UniqueConstraint("student_id", "session_id", name="uq_student_session_attendance"),
    )

    id: Mapped[object] = guid_pk()
    session_id: Mapped[object] = mapped_column(guid(), ForeignKey("attendance_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    student_id: Mapped[object] = mapped_column(guid(), ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(SAEnum(AttendanceStatus), default=AttendanceStatus.PRESENT, nullable=False)
    marked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    verification_method: Mapped[str] = mapped_column(String(40), default="QR_SCAN", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    session = relationship("AttendanceSession", back_populates="records")
    student = relationship("Student")
