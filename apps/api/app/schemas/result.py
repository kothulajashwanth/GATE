from datetime import datetime

from pydantic import BaseModel


class ResultOut(BaseModel):
    id: str
    examId: str
    examTitle: str | None = None
    totalMarks: float
    obtainedMarks: float
    percentage: float | None = None
    rank: int | None = None
    isPassed: bool | None = None
    status: str
    publishedAt: datetime | None = None
    questionAnalysis: dict | None = None
