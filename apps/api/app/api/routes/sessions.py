from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.errors import BadRequestError, NotFoundError
from app.db.models.exam import Exam
from app.db.models.session import ExamSession, SessionAnswer, SessionStatus, ViolationRecord
from app.db.models.student import Student
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.pagination import PaginatedResponse
from app.services.audit import AuditService
from app.services.exam_engine import ExamEngine

router = APIRouter()


class SessionOut(BaseModel):
    id: str
    examId: str
    studentId: str
    studentRollNumber: str | None = None
    studentName: str | None = None
    status: str
    startedAt: str
    submittedAt: str | None = None
    deadlineAt: str
    warningCount: int
    score: float | None = None
    timeSpentSeconds: int | None = None
    securityStatus: str = "NORMAL"


class TimelineEventOut(BaseModel):
    id: str
    violationType: str
    warningNumber: int
    reason: str | None = None
    createdAt: str


class AdminTerminateRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


import logging

logger = logging.getLogger("app")


def _session_out(s: ExamSession, student: Student | None = None) -> SessionOut:
    sec_status = "NORMAL"
    status_str = s.status.value if hasattr(s.status, "value") else str(s.status)
    if status_str == SessionStatus.TERMINATED.value or status_str == "TERMINATED":
        sec_status = "TERMINATED"
    elif s.warning_count >= 2:
        sec_status = "HIGH_RISK"
    elif s.warning_count == 1:
        sec_status = "WARNING"

    return SessionOut(
        id=str(s.id),
        examId=str(s.exam_id),
        studentId=str(s.student_id),
        studentRollNumber=student.roll_number if student else None,
        studentName=student.user.full_name if (student and student.user) else None,
        status=status_str,
        startedAt=s.started_at.isoformat() if s.started_at else "",
        submittedAt=s.submitted_at.isoformat() if s.submitted_at else None,
        deadlineAt=s.deadline_at.isoformat() if s.deadline_at else "",
        warningCount=s.warning_count,
        score=s.score,
        timeSpentSeconds=s.time_spent_seconds,
        securityStatus=sec_status,
    )


@router.get("", response_model=PaginatedResponse[SessionOut], summary="List exam sessions (live monitoring)")
async def list_sessions(
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
    session_status: str | None = None,
    exam_id: str | None = None,
) -> PaginatedResponse[SessionOut]:
    logger.info(f"[EXAM_SESSIONS] REQUEST RECEIVED: page={page}, page_size={page_size}")
    logger.info(f"[EXAM_SESSIONS] AUTHENTICATION PASSED: user_id={actor.id}, email={actor.email}, role={actor.role}")
    logger.info("[EXAM_SESSIONS] STARTING DATABASE QUERY")
    base = select(ExamSession).order_by(ExamSession.started_at.desc())
    if session_status and session_status != "all":
        try:
            base = base.where(ExamSession.status == SessionStatus(session_status))
        except ValueError:
            pass
    if exam_id:
        base = base.where(ExamSession.exam_id == exam_id)

    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    result = await db.execute(base.limit(page_size).offset((page - 1) * page_size))
    sessions = result.scalars().all()

    items = []
    for s in sessions:
        student = (await db.execute(select(Student).where(Student.id == s.student_id))).scalar_one_or_none()
        items.append(_session_out(s, student))

    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(items=items, page=page, pageSize=page_size, total=total, totalPages=total_pages)


@router.get("/{session_id}/timeline", response_model=list[TimelineEventOut], summary="Security violation timeline")
async def get_session_timeline(
    session_id: str,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TimelineEventOut]:
    result = await db.execute(
        select(ViolationRecord)
        .where(ViolationRecord.session_id == session_id)
        .order_by(ViolationRecord.created_at.asc())
    )
    records = result.scalars().all()
    return [
        TimelineEventOut(
            id=str(r.id),
            violationType=r.violation_type,
            warningNumber=r.warning_number,
            reason=r.reason,
            createdAt=r.created_at.isoformat(),
        )
        for r in records
    ]


@router.post("/{session_id}/admin-terminate", response_model=SessionOut, summary="Force terminate active exam session by Admin")
async def admin_terminate_session(
    session_id: str,
    body: AdminTerminateRequest,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionOut:
    result = await db.execute(select(ExamSession).where(ExamSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise NotFoundError("Session not found")
    if session.status != SessionStatus.ACTIVE:
        raise BadRequestError(f"Session is in {session.status.value} status, cannot terminate")

    engine = ExamEngine(db)
    session = await engine.admin_terminate_session(session, body.reason, str(actor.id))

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="ADMIN_TERMINATED_EXAM",
        entity_type="exam_session",
        entity_id=session_id,
        new_value={"reason": body.reason, "status": "terminated"},
    )
    await db.commit()

    student = (await db.execute(select(Student).where(Student.id == session.student_id))).scalar_one_or_none()
    return _session_out(session, student)