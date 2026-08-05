from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    String,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin, guid, guid_pk


class ResultStatus(StrEnum):
    PENDING = "pending"
    AUTO = "auto"
    MANUAL = "manual"
    PUBLISHED = "published"


class ExamResult(Base, TimestampMixin):
    """Computed result for a completed exam session. 1:1 with exam_sessions."""

    __tablename__ = "exam_results"

    id: Mapped[object] = guid_pk()
    session_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("exam_sessions.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    exam_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("exams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[ResultStatus] = mapped_column(
        SAEnum(ResultStatus, name="result_status"), default=ResultStatus.PENDING, index=True, nullable=False
    )
    total_marks: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    obtained_marks: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    percentage: Mapped[float | None] = mapped_column(nullable=True)
    rank: Mapped[int | None] = mapped_column(nullable=True)
    is_passed: Mapped[bool | None] = mapped_column(nullable=True)
    evaluated_by: Mapped[str] = mapped_column(String(20), default="auto", nullable=False)  # auto | manual
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    question_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    time_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    feedback: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    session = relationship("ExamSession")
    exam = relationship("Exam")
    student = relationship("Student")
