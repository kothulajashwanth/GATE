from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.db.models.session import ExamSession, SessionStatus
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.pagination import PaginatedResponse

router = APIRouter()


class SessionOut(BaseModel):
    id: str
    examId: str
    studentId: str
    status: str
    startedAt: str
    submittedAt: str | None = None
    deadlineAt: str
    warningCount: int
    score: float | None = None
    timeSpentSeconds: int | None = None


def _session_out(s: ExamSession) -> SessionOut:
    return SessionOut(
        id=str(s.id),
        examId=str(s.exam_id),
        studentId=str(s.student_id),
        status=s.status.value,
        startedAt=s.started_at.isoformat(),
        submittedAt=s.submitted_at.isoformat() if s.submitted_at else None,
        deadlineAt=s.deadline_at.isoformat(),
        warningCount=s.warning_count,
        score=s.score,
        timeSpentSeconds=s.time_spent_seconds,
    )


@router.get("", response_model=PaginatedResponse[SessionOut], summary="List exam sessions (live monitoring)")
async def list_sessions(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
    session_status: str | None = None,
    exam_id: str | None = None,
) -> PaginatedResponse[SessionOut]:
    base = select(ExamSession).order_by(ExamSession.started_at.desc())
    if session_status:
        base = base.where(ExamSession.status == SessionStatus(session_status))
    if exam_id:
        base = base.where(ExamSession.exam_id == exam_id)

    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    result = await db.execute(base.limit(page_size).offset((page - 1) * page_size))
    items = [_session_out(s) for s in result.scalars().all()]
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(items=items, page=page, pageSize=page_size, total=total, totalPages=total_pages)