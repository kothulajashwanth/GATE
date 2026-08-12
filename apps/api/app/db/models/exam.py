from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, SoftDeleteMixin, TimestampMixin, guid, guid_pk


class ExamStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    LIVE = "live"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class ExamQuestionMode(StrEnum):
    ALL_AT_ONCE = "all_at_once"
    ONE_AT_A_TIME = "one_at_a_time"


class Exam(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "exams"

    id: Mapped[object] = guid_pk()
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    subject_id: Mapped[object | None] = mapped_column(
        guid(), ForeignKey("subjects.id"), index=True, nullable=True
    )
    created_by: Mapped[object] = mapped_column(guid(), ForeignKey("users.id"), nullable=False)

    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    passing_marks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    negative_marks_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    negative_marks_value: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    randomize_questions: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    shuffle_options: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    attempt_limit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    question_mode: Mapped[ExamQuestionMode] = mapped_column(
        SAEnum(ExamQuestionMode, name="exam_question_mode"), default=ExamQuestionMode.ALL_AT_ONCE, nullable=False
    )
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), default="private", nullable=False)  # private | public
    status: Mapped[ExamStatus] = mapped_column(
        SAEnum(ExamStatus, name="exam_status"), default=ExamStatus.DRAFT, index=True, nullable=False
    )
    total_marks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    security_mode: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    camera_proctoring_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_submit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    questions = relationship(
        "ExamQuestion", back_populates="exam", cascade="all, delete-orphan", order_by="ExamQuestion.order_index"
    )
    schedules = relationship(
        "ExamSchedule", back_populates="exam", cascade="all, delete-orphan"
    )

    @property
    def duration(self) -> int:
        return self.duration_minutes

    @property
    def start_time(self) -> datetime:
        return self.start_at

    @property
    def end_time(self) -> datetime:
        return self.end_at

    @property
    def randomize_options(self) -> bool:
        return self.shuffle_options

    @property
    def negative_marks(self) -> float:
        return self.negative_marks_value


class ExamQuestion(Base):
    """Exam-question join with per-exam ordering and marks override."""

    __tablename__ = "exam_questions"

    id: Mapped[object] = guid_pk()
    exam_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("exams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    marks: Mapped[int] = mapped_column(Integer, nullable=False)

    exam = relationship("Exam", back_populates="questions")
    question = relationship("Question")

    @property
    def display_order(self) -> int:
        return self.order_index


class ExamSchedule(Base, TimestampMixin):
    """Target audience for an exam: department / semester / section scoping."""

    __tablename__ = "exam_schedules"

    id: Mapped[object] = guid_pk()
    exam_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("exams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    department_id: Mapped[object | None] = mapped_column(guid(), ForeignKey("departments.id"), nullable=True)
    semester_id: Mapped[object | None] = mapped_column(guid(), ForeignKey("semesters.id"), nullable=True)
    section_id: Mapped[object | None] = mapped_column(guid(), ForeignKey("sections.id"), nullable=True)

    exam = relationship("Exam", back_populates="schedules")
