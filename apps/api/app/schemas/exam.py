from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExamCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    subjectId: str | None = None
    durationMinutes: int = Field(gt=0, le=1440)
    startAt: datetime
    endAt: datetime
    passingMarks: int = 0
    negativeMarksEnabled: bool = False
    negativeMarksValue: float = 0.0
    randomizeQuestions: bool = True
    shuffleOptions: bool = True
    attemptLimit: int = Field(default=1, ge=1, le=10)
    questionMode: str = "all_at_once"
    instructions: str | None = None
    visibility: str = "private"
    securityMode: bool = True
    cameraProctoringEnabled: bool = False
    autoSubmit: bool = True


class ExamUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    subjectId: str | None = None
    durationMinutes: int | None = None
    startAt: datetime | None = None
    endAt: datetime | None = None
    passingMarks: int | None = None
    negativeMarksEnabled: bool | None = None
    negativeMarksValue: float | None = None
    randomizeQuestions: bool | None = None
    shuffleOptions: bool | None = None
    attemptLimit: int | None = None
    questionMode: str | None = None
    instructions: str | None = None
    visibility: str | None = None
    securityMode: bool | None = None
    cameraProctoringEnabled: bool | None = None
    autoSubmit: bool | None = None
    status: str | None = None


class ExamOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    subjectId: str | None = None
    durationMinutes: int
    startAt: datetime
    endAt: datetime
    passingMarks: int
    negativeMarksEnabled: bool
    negativeMarksValue: float
    randomizeQuestions: bool
    shuffleOptions: bool
    attemptLimit: int
    questionMode: str
    instructions: str | None = None
    visibility: str
    status: str
    totalMarks: int
    securityMode: bool
    cameraProctoringEnabled: bool
    autoSubmit: bool
    createdAt: datetime
    updatedAt: datetime


class ExamQuestionLink(BaseModel):
    questionId: str
    marks: int = 1


class ExamQuestionsUpdate(BaseModel):
    """Attach/detach questions to an exam, replacing the current set."""

    questions: list[ExamQuestionLink]
