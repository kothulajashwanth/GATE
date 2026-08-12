from app.db.models.academic import Department, Section, Semester, Topic
from app.db.models.audit import AuditLog
from app.db.models.base import Base, SoftDeleteMixin, TimestampMixin
from app.db.models.exam import Exam, ExamQuestion, ExamSchedule
from app.db.models.notification import Notification
from app.db.models.question import (
    FailedQuestion,
    Question,
    QuestionBankFolder,
    QuestionOption,
    QuestionVersion,
    Subject,
    UploadedFile,
)
from app.db.models.result import ExamResult
from app.db.models.session import ExamSession, SessionAnswer, ViolationRecord
from app.db.models.student import Student
from app.db.models.user import User
from app.db.models.student_communication import StudentQuery, Feedback # Added

__all__ = [
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "User",
    "Department",
    "Semester",
    "Section",
    "Topic",
    "Student",
    "QuestionBankFolder",
    "Subject",
    "Topic",
    "UploadedFile",
    "FailedQuestion",
    "Question",
    "QuestionOption",
    "QuestionVersion",
    "Exam",
    "ExamQuestion",
    "ExamSchedule",
    "ExamSession",
    "SessionAnswer",
    "ViolationRecord",
    "ExamResult",
    "AuditLog",
    "Notification",
    "StudentQuery", # Added
    "Feedback", # Added
]
