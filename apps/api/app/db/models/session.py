from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin, guid, guid_pk


class SessionStatus(StrEnum):
    ACTIVE = "active"
    SUBMITTED = "submitted"
    TERMINATED = "terminated"
    EXPIRED = "expired"


class ExamSession(Base, TimestampMixin):
    """One student's run of one exam. At most one ACTIVE row per student+exam."""

    __tablename__ = "exam_sessions"

    id: Mapped[object] = guid_pk()
    exam_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("exams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus, name="session_status"), default=SessionStatus.ACTIVE, index=True, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    terminated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    terminate_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    device_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    score: Mapped[float | None] = mapped_column(nullable=True)
    time_spent_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # future attempts locked

    exam = relationship("Exam")
    student = relationship("Student")
    answers = relationship(
        "SessionAnswer",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionAnswer.question_id",
    )
    violations = relationship(
        "ViolationRecord",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ViolationRecord.created_at",
    )

    @property
    def warnings(self) -> int:
        return self.warning_count

    @property
    def termination_reason(self) -> str | None:
        return self.terminate_reason

    @property
    def percentage(self) -> float | None:
        if self.score is not None and self.exam and self.exam.total_marks > 0:
            return round((self.score / self.exam.total_marks) * 100, 2)
        return None

    __table_args__ = (
        Index("ix_sessions_student_exam_active", "student_id", "exam_id", "status"),
    )


class SessionAnswer(Base, TimestampMixin):
    __tablename__ = "session_answers"

    id: Mapped[object] = guid_pk()
    session_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("exam_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    question_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    selected_option_id: Mapped[object | None] = mapped_column(
        guid(), ForeignKey("question_options.id"), index=True, nullable=True
    )
    answer: Mapped[list] = mapped_column(JSON, default=list, nullable=False)  # normalized answer payload
    is_answered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_correct: Mapped[bool | None] = mapped_column(nullable=True)
    marks_awarded: Mapped[float | None] = mapped_column(nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_taken_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    session = relationship("ExamSession", back_populates="answers")
    question = relationship("Question")
    selected_option = relationship("QuestionOption")

    @property
    def attempt_id(self) -> object:
        return self.session_id

    @property
    def answered_at(self) -> datetime:
        return self.created_at


class ViolationType(StrEnum):
    TAB_SWITCH = "tab_switch"
    TAB_CHANGE = "tab_change"
    WINDOW_BLUR = "window_blur"
    FULLSCREEN_EXIT = "fullscreen_exit"
    COPY_ATTEMPT = "copy_attempt"
    PASTE_ATTEMPT = "paste_attempt"
    RIGHT_CLICK = "right_click"
    KEYBOARD_SHORTCUT = "keyboard_shortcut"
    VISIBILITY_CHANGE = "visibility_change"
    WINDOW_MINIMIZE = "window_minimize"
    REFRESH = "refresh"
    BACK_NAVIGATION = "back_navigation"
    COPY = "copy"
    PASTE = "paste"
    TEXT_SELECTION = "text_selection"
    DEVTOOLS = "devtools"
    MOUSE_LEAVE = "mouse_leave"
    NETWORK_DISCONNECT = "network_disconnect"
    RESIZE = "resize"


class ViolationRecord(Base, TimestampMixin):
    __tablename__ = "violation_records"

    id: Mapped[object] = guid_pk()
    session_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("exam_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    violation_type: Mapped[ViolationType] = mapped_column(
        SAEnum(ViolationType, name="violation_type"), index=True, nullable=False
    )
    warning_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    action_taken: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    device_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)

    session = relationship("ExamSession", back_populates="violations")

    @property
    def description(self) -> str | None:
        return self.reason

    @property
    def timestamp(self) -> datetime:
        return self.created_at
