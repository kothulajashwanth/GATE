from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, TimestampMixin, guid, guid_pk


class QueryStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class StudentQuery(Base, TimestampMixin):
    __tablename__ = "student_queries"

    id: Mapped[UUID] = guid_pk()
    student_id: Mapped[UUID] = mapped_column(guid(), ForeignKey("students.id"), index=True, nullable=False)
    exam_id: Mapped[UUID | None] = mapped_column(guid(), ForeignKey("exams.id"), index=True, nullable=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[QueryStatus] = mapped_column(
        SAEnum(QueryStatus, name="query_status"), default=QueryStatus.OPEN, index=True, nullable=False
    )

    student = relationship("Student", back_populates="queries") # Assuming student model will have 'queries' relationship
    exam = relationship("Exam")


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedbacks"

    id: Mapped[UUID] = guid_pk()
    student_id: Mapped[UUID | None] = mapped_column(guid(), ForeignKey("students.id"), index=True, nullable=True) # Nullable for anonymous
    exam_id: Mapped[UUID | None] = mapped_column(guid(), ForeignKey("exams.id"), index=True, nullable=True)
    feedback_text: Mapped[str] = mapped_column(Text, nullable=False)
    anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    student = relationship("Student", back_populates="feedbacks") # Assuming student model will have 'feedbacks' relationship
    exam = relationship("Exam")