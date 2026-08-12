from typing import Annotated
import json # Added
from datetime import datetime, UTC # Added UTC for consistency

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from redis.asyncio import Redis # Added

from app.core.auth import require_roles
from app.core.errors import NotFoundError
from app.db.models.exam import Exam
from app.db.models.question import Question
from app.db.models.session import ExamSession, SessionStatus
from app.db.models.student import Student
from app.db.models.user import Role, User
from app.db.redis import get_redis_dep # Added
from app.db.session import get_db
from app.services.exam_engine import ExamEngine
from app.schemas.active_session import StudentSessionData # Added
from app.core.config import get_settings # Added

router = APIRouter()

EXAM_SESSION_REDIS_TTL_SECONDS = 60 * 60 * 24 # 24 hours, enough for any exam


class StartRequest(BaseModel):
    examId: str


class AnswerRequest(BaseModel):
    questionId: str
    answer: list = Field(default_factory=list)


class HeartbeatRequest(BaseModel):
    warningCount: int = Field(ge=0, le=100)


class ViolationRequest(BaseModel):
    violationType: str
    reason: str | None = None


class QuestionView(BaseModel):
    id: str
    type: str
    text: str
    options: list[str] | None = None
    imageUrl: str | None = None
    marks: int
    negativeMarks: float
    isAnswered: bool = False


class SessionView(BaseModel):
    sessionId: str
    examId: str
    examTitle: str
    examInstructions: str | None = None
    startedAt: str
    deadlineAt: str
    durationMinutes: int
    warningCount: int
    maxWarnings: int
    status: str
    questions: list[QuestionView]
    questionMode: str
    securityMode: bool
    negativeMarksEnabled: bool
    negativeMarksValue: float


async def _student_or_404(db: AsyncSession, user: User) -> Student:
    result = await db.execute(select(Student).where(Student.user_id == user.id))
    student = result.scalar_one_or_one()
    if student is None:
        raise NotFoundError("Student profile not found. Contact administration.")
    return student


async def _exam_or_404(db: AsyncSession, exam_id: str) -> Exam:
    result = await db.execute(select(Exam).where(Exam.id == exam_id, Exam.deleted_at.is_(None)))
    exam = result.scalar_one_or_none()
    if exam is None:
        raise NotFoundError("Exam not found")
    return exam


async def _session_or_404(db: AsyncSession, session_id: str) -> ExamSession:
    result = await db.execute(select(ExamSession).where(ExamSession.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise NotFoundError("Session not found")
    return session


def _to_view(session: ExamSession, exam: Exam, questions: list[Question], answered: set[str]) -> SessionView:
    return SessionView(
        sessionId=str(session.id),
        examId=str(exam.id),
        examTitle=exam.title,
        examInstructions=exam.instructions,
        startedAt=session.started_at.isoformat(),
        deadlineAt=session.deadline_at.isoformat(),
        durationMinutes=exam.duration_minutes,
        warningCount=session.warning_count,
        maxWarnings=3,
        status=session.status.value,
        questions=[
            QuestionView(
                id=str(q.id),
                type=q.type.value,
                text=q.text,
                options=q.options,
                imageUrl=q.image_url,
                marks=q.marks,
                negativeMarks=q.negative_marks,
                isAnswered=str(q.id) in answered,
            )
            for q in questions
        ],
        questionMode=exam.question_mode.value,
        securityMode=exam.security_mode,
        negativeMarksEnabled=exam.negative_marks_enabled,
        negativeMarksValue=exam.negative_marks_value,
    )


@router.post("/start", response_model=SessionView, summary="Start or resume an exam session")
async def start_exam(
    body: StartRequest,
    request: Request,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis_dep)], # Added redis dependency
) -> SessionView:
    student = await _student_or_404(db, user)
    exam = await _exam_or_404(db, body.examId)
    engine = ExamEngine(db)

    session = await engine.start_session(
        student,
        exam,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        fingerprint=request.headers.get("x-device-fingerprint"),
    )
    questions = await engine.get_questions(exam, session)

    # answered question ids
    result = await db.execute(select(ExamSession).where(ExamSession.id == session.id))
    full = result.scalar_one()
    answered = {str(a.question_id) for a in full.answers}

    await db.commit()

    # Update active student session in Redis
    redis_key = f"active_student_sessions:{user.id}"
    student_session_json = await redis.get(redis_key)

    if student_session_json:
        # Update existing session data
        existing_session_data = StudentSessionData.model_validate_json(student_session_json)
        existing_session_data.exam_id = exam.id
        existing_session_data.status = "in_exam"
        existing_session_data.last_activity = datetime.now(UTC)
        await redis.set(redis_key, existing_session_data.model_dump_json(), ex=EXAM_SESSION_REDIS_TTL_SECONDS)
    else:
        # Create new session data if not found (should not happen if login worked)
        new_session_data = StudentSessionData(
            user_id=user.id,
            login_time=datetime.now(UTC), # Approx, if not found in redis
            exam_id=exam.id,
            status="in_exam",
            last_activity=datetime.now(UTC)
        )
        await redis.set(redis_key, new_session_data.model_dump_json(), ex=EXAM_SESSION_REDIS_TTL_SECONDS)

    return _to_view(session, exam, questions, answered)


@router.get("/{session_id}", response_model=SessionView, summary="Resume existing session")
async def get_session(
    session_id: str,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionView:
    session = await _session_or_404(db, session_id)
    if session.student_id != (await _student_or_404(db, user)).id:
        from app.core.errors import ForbiddenError

        raise ForbiddenError("Not your session")
    exam = await _exam_or_404(db, str(session.exam_id))
    engine = ExamEngine(db)
    questions = await engine.get_questions(exam, session)
    answered = {str(a.question_id) for a in session.answers}
    return _to_view(session, exam, questions, answered)


@router.post("/{session_id}/answer", response_model=dict, summary="Save an answer (auto-save)")
async def save_answer(
    session_id: str,
    body: AnswerRequest,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    session = await _session_or_404(db, session_id)
    engine = ExamEngine(db)
    await engine.save_answer(session, body.questionId, body.answer)
    await db.commit()
    return {"saved": True}


@router.post("/{session_id}/heartbeat", response_model=dict, summary="Client heartbeat (warnings + time)")
async def heartbeat(
    session_id: str,
    body: HeartbeatRequest,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis_dep)], # Added redis dependency
) -> dict:
    session = await _session_or_404(db, session_id)
    engine = ExamEngine(db)
    session = await engine.heartbeat(session, body.warningCount)
    await db.commit()

    # Update active student session in Redis
    redis_key = f"active_student_sessions:{user.id}"
    student_session_json = await redis.get(redis_key)

    if student_session_json:
        existing_session_data = StudentSessionData.model_validate_json(student_session_json)
        existing_session_data.exam_id = session.exam_id # Ensure exam_id is set
        existing_session_data.status = "in_exam" # Ensure status is "in_exam"
        existing_session_data.last_activity = datetime.now(UTC)
        await redis.set(redis_key, existing_session_data.model_dump_json(), ex=EXAM_SESSION_REDIS_TTL_SECONDS)
    else:
        # Recreate if somehow lost (should be rare)
        new_session_data = StudentSessionData(
            user_id=user.id,
            login_time=datetime.now(UTC), # Approx
            exam_id=session.exam_id,
            status="in_exam",
            last_activity=datetime.now(UTC)
        )
        await redis.set(redis_key, new_session_data.model_dump_json(), ex=EXAM_SESSION_REDIS_TTL_SECONDS)

    return {
        "status": session.status.value,
        "warningCount": session.warning_count,
        "locked": session.is_locked,
        "deadlineAt": session.deadline_at.isoformat(),
    }


@router.post("/{session_id}/violation", response_model=dict, summary="Record a proctoring violation")
async def record_violation(
    session_id: str,
    body: ViolationRequest,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    session = await _session_or_404(db, session_id)
    engine = ExamEngine(db)
    session = await engine.record_violation(session, body.violationType, body.reason)
    await db.commit()
    return {
        "status": session.status.value,
        "warningCount": session.warning_count,
        "terminated": session.status == SessionStatus.TERMINATED,
        "maxWarnings": 3,
    }


@router.post("/{session_id}/submit", response_model=dict, summary="Submit the exam")
async def submit(
    session_id: str,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    session = await _session_or_404(db, session_id)
    engine = ExamEngine(db)
    session = await engine.submit(session)

    # auto-evaluate objective questions; subjective flagged for manual review
    from app.services.results import ResultCalculator

    calc = ResultCalculator(db)
    await calc.evaluate_session(session)
    await calc.compute_ranks(str(session.exam_id))
    await db.commit()
    return {"status": session.status.value, "submitted": True, "evaluated": True}