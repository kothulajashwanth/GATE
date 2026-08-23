import enum
import uuid
from datetime import date, datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, UniqueConstraint, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.academic import Department, Section, Semester
    from app.db.models.question import Subject
    from app.db.models.student import Student
    from app.db.models.user import User


class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"


class SessionState(str, enum.Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class AttendanceSession(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "attendance_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), ForeignKey("subjects.id"), nullable=False)
    department_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("departments.id"), nullable=True)
    semester_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("semesters.id"), nullable=True)
    section_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("sections.id"), nullable=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    start_time: Mapped[str] = mapped_column(String(10), nullable=False, default="09:00")
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    status: Mapped[SessionState] = mapped_column(
        Enum(SessionState), nullable=False, default=SessionState.ACTIVE
    )
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)

    subject: Mapped["Subject"] = relationship("Subject")
    department: Mapped[Optional["Department"]] = relationship("Department")
    semester: Mapped[Optional["Semester"]] = relationship("Semester")
    section: Mapped[Optional["Section"]] = relationship("Section")
    creator: Mapped["User"] = relationship("User")
    records: Mapped[list["AttendanceRecord"]] = relationship(
        "AttendanceRecord", back_populates="session", cascade="all, delete-orphan"
    )


class AttendanceRecord(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_session_student"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("attendance_sessions.id"), nullable=False)
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id"), nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus), nullable=False, default=AttendanceStatus.PRESENT
    )
    remarks: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    marked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    session: Mapped["AttendanceSession"] = relationship("AttendanceSession", back_populates="records")
    student: Mapped["Student"] = relationship("Student")
