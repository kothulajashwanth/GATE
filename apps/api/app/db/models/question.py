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
    Text,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base, SoftDeleteMixin, TimestampMixin, guid, guid_pk


class QuestionType(StrEnum):
    MCQ = "mcq"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    PARAGRAPH = "paragraph"
    CODING = "coding"
    IMAGE_BASED = "image_based"
    MULTI_SELECT = "multi_select"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class BloomLevel(StrEnum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


class QuestionBankFolder(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "question_bank_folders"

    id: Mapped[object] = guid_pk()
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    parent_id: Mapped[object | None] = mapped_column(
        guid(), ForeignKey("question_bank_folders.id"), nullable=True
    )
    created_by: Mapped[object] = mapped_column(guid(), ForeignKey("users.id"), nullable=False)

    parent = relationship("QuestionBankFolder", remote_side=[id], backref="children")


class Subject(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "subjects"

    id: Mapped[object] = guid_pk()
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    department_id: Mapped[object | None] = mapped_column(
        guid(), ForeignKey("departments.id"), nullable=True
    )

    department = relationship("Department")
    topics = relationship("Topic", back_populates="subject", cascade="all, delete-orphan")


class UploadedFile(Base, TimestampMixin):
    """File uploaded to Question Repository (PDF, DOCX, TXT, Excel)."""

    __tablename__ = "uploaded_files"

    id: Mapped[object] = guid_pk()
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="processing", nullable=False)  # parsed, processing, failed
    uploaded_by: Mapped[object] = mapped_column(guid(), ForeignKey("users.id"), nullable=False)
    questions_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    @property
    def filename(self) -> str:
        return self.file_name

    @property
    def storage_path(self) -> str | None:
        return self.storage_url

    @property
    def processing_status(self) -> str:
        return self.status

    @property
    def questions_extracted(self) -> int:
        return self.questions_found


class FailedQuestion(Base, TimestampMixin):
    """Queue for questions that failed validation pipeline."""

    __tablename__ = "failed_questions"

    id: Mapped[object] = guid_pk()
    source_file_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("uploaded_files.id", ondelete="CASCADE"), nullable=False
    )
    raw_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class QuestionOption(Base, TimestampMixin):
    """Question option stored separately for MCQs and multi-select questions."""

    __tablename__ = "question_options"

    id: Mapped[object] = guid_pk()
    question_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    question = relationship("Question", back_populates="options_rel")


class Question(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "questions"

    id: Mapped[object] = guid_pk()
    folder_id: Mapped[object | None] = mapped_column(
        guid(), ForeignKey("question_bank_folders.id"), index=True, nullable=True
    )
    subject_id: Mapped[object | None] = mapped_column(
        guid(), ForeignKey("subjects.id"), index=True, nullable=True
    )
    topic_id: Mapped[object | None] = mapped_column(
        guid(), ForeignKey("topics.id"), index=True, nullable=True
    )
    source_file_id: Mapped[object | None] = mapped_column(
        guid(), ForeignKey("uploaded_files.id"), index=True, nullable=True
    )
    created_by: Mapped[object] = mapped_column(guid(), ForeignKey("users.id"), nullable=False)

    type: Mapped[QuestionType] = mapped_column(
        SAEnum(QuestionType, name="question_type"), index=True, nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    options: Mapped[list] = mapped_column(JSON, nullable=True)  # ["A", "B", ...] for legacy/JSON compatibility
    correct_answers: Mapped[list] = mapped_column(JSON, nullable=False)  # ["A"] / index for fill_blank
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty: Mapped[Difficulty] = mapped_column(
        SAEnum(Difficulty, name="question_difficulty"), default=Difficulty.MEDIUM, nullable=False
    )
    bloom_level: Mapped[BloomLevel | None] = mapped_column(
        SAEnum(BloomLevel, name="bloom_level"), nullable=True
    )
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    marks: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    negative_marks: Mapped[float] = mapped_column(default=0.0, nullable=False)
    topic: Mapped[str | None] = mapped_column(String(200), nullable=True)
    learning_outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # source tracking for AI improvements
    derived_from_id: Mapped[object | None] = mapped_column(
        guid(), ForeignKey("questions.id"), nullable=True
    )

    options_rel = relationship(
        "QuestionOption",
        back_populates="question",
        order_by="QuestionOption.display_order",
        cascade="all, delete-orphan",
    )
    versions = relationship(
        "QuestionVersion",
        back_populates="question",
        order_by="QuestionVersion.version.desc()",
        cascade="all, delete-orphan",
    )
    folder = relationship("QuestionBankFolder")
    subject = relationship("Subject")
    topic_rel = relationship("Topic")
    source_file = relationship("UploadedFile")

    @property
    def question_text(self) -> str:
        return self.text

    @property
    def question_type(self) -> QuestionType:
        return self.type

    @property
    def ai_generated(self) -> bool:
        return self.is_ai_generated

    @property
    def status(self) -> str:
        return "verified" if self.is_verified else "draft"

    __table_args__ = (
        Index("ix_questions_subject_difficulty", "subject_id", "difficulty"),
        Index("ix_questions_topic_id", "topic_id"),
        Index("ix_questions_type_bloom", "type", "bloom_level"),
    )


class QuestionVersion(Base):
    """Immutable snapshot of a question for version history / rollback."""

    __tablename__ = "question_versions"

    id: Mapped[object] = guid_pk()
    question_id: Mapped[object] = mapped_column(
        guid(), ForeignKey("questions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)  # full question payload
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_by: Mapped[object] = mapped_column(guid(), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    question = relationship("Question", back_populates="versions")
