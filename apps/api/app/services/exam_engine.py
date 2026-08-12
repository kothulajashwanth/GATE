"""Exam session lifecycle: start, answer, heartbeat, violation, submit.

The engine owns the anti-cheating invariants:
- one ACTIVE session per student+exam
- no session before start_at / after end_at
- deadline = now + duration (not server start + duration offset by clock)
- warning limit reached => terminate + lock future attempts
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.db.models.exam import Exam, ExamQuestion, ExamStatus
from app.db.models.question import Question
from app.db.models.session import ExamSession, SessionAnswer, SessionStatus, ViolationRecord
from app.db.models.student import Student
from app.db.models.user import User

MAX_WARNINGS = 3


class ExamEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---------- lifecycle ----------

    async def start_session(self, student: Student, exam: Exam, *, ip: str | None, user_agent: str | None, fingerprint: str | None) -> ExamSession:
        now = datetime.now(UTC)

        if exam.status not in (ExamStatus.PUBLISHED, ExamStatus.IN_PROGRESS):
            raise ValidationError("Exam is not open", details={"code": "exam_not_open"})
        if now < exam.start_at:
            raise ValidationError("Exam has not started yet", details={"code": "exam_not_started"})
        if now > exam.end_at:
            raise ValidationError("Exam window has closed", details={"code": "exam_closed"})

        # one active session per student+exam
        existing = await self.db.execute(
            select(ExamSession).where(
                ExamSession.student_id == student.id,
                ExamSession.exam_id == exam.id,
                ExamSession.status == SessionStatus.ACTIVE,
            )
        )
        active = existing.scalar_one_or_none()
        if active is not None:
            return active  # idempotent resume

        # attempt limit
        completed = await self.db.execute(
            select(ExamSession).where(
                ExamSession.student_id == student.id,
                ExamSession.exam_id == exam.id,
                ExamSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.EXPIRED, SessionStatus.TERMINATED]),
            )
        )
        finished = completed.scalars().all()
        locked = [s for s in finished if s.is_locked]
        if locked:
            raise ForbiddenError(
                "You are permanently locked out of this exam due to a security violation",
                details={"code": "session_locked"},
            )
        if len(finished) >= exam.attempt_limit:
            raise ForbiddenError("Attempt limit reached", details={"code": "attempt_limit"})

        deadline = now + timedelta(minutes=exam.duration_minutes)
        session = ExamSession(
            exam_id=exam.id,
            student_id=student.id,
            status=SessionStatus.ACTIVE,
            started_at=now,
            deadline_at=deadline,
            ip_address=ip,
            user_agent=user_agent,
            device_fingerprint=fingerprint,
        )
        self.db.add(session)
        await self.db.flush()
        return session

    async def get_questions(self, exam: Exam, session: ExamSession) -> list[Question]:
        """Question set for the session, honoring randomize_questions."""
        result = await self.db.execute(
            select(ExamQuestion)
            .where(ExamQuestion.exam_id == exam.id)
            .order_by(ExamQuestion.order_index)
        )
        links = result.scalars().all()
        qids = [l.question_id for l in links]
        if not qids:
            raise NotFoundError("Exam has no questions")
        result = await self.db.execute(
            select(Question).where(Question.id.in_(qids), Question.deleted_at.is_(None))
        )
        questions = {str(q.id): q for q in result.scalars().all()}
        ordered = [questions[str(qid)] for qid in qids if str(qid) in questions]

        if exam.randomize_questions:
            import random

            random.shuffle(ordered)
        return ordered

    async def save_answer(self, session: ExamSession, question_id: str, answer: list) -> SessionAnswer:
        """Upsert an answer. Validates the session is active and in time."""
        now = datetime.now(UTC)
        if session.status != SessionStatus.ACTIVE:
            raise ValidationError("Session is not active", details={"code": "session_not_active"})
        if now > session.deadline_at:
            await self._expire(session)
            raise ValidationError("Time is up", details={"code": "time_up"})

        result = await self.db.execute(
            select(SessionAnswer).where(
                SessionAnswer.session_id == session.id,
                SessionAnswer.question_id == question_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            row = SessionAnswer(
                session_id=session.id,
                question_id=question_id,
                answer=answer,
                is_answered=bool(answer),
            )
            self.db.add(row)
        else:
            row.answer = answer
            row.is_answered = bool(answer)
        await self.db.flush()
        return row

    async def heartbeat(self, session: ExamSession, warning_count: int) -> ExamSession:
        """Client syncs its warning count with the server truth."""
        now = datetime.now(UTC)
        if now > session.deadline_at and session.status == SessionStatus.ACTIVE:
            await self._expire(session)
            return session
        if warning_count > session.warning_count:
            session.warning_count = warning_count
            if warning_count >= MAX_WARNINGS:
                await self._terminate(session, "Maximum warnings reached")
        await self.db.flush()
        return session

    async def record_violation(self, session: ExamSession, violation_type: str, reason: str | None = None) -> ExamSession:
        """Increment warning count, persist the violation, terminate at 3."""
        now = datetime.now(UTC)
        if session.status != SessionStatus.ACTIVE:
            return session

        session.warning_count += 1
        warning_number = session.warning_count
        self.db.add(
            ViolationRecord(
                session_id=session.id,
                violation_type=violation_type,
                warning_number=warning_number,
                reason=reason,
                ip_address=session.ip_address,
                user_agent=session.user_agent,
                device_fingerprint=session.device_fingerprint,
            )
        )
        if warning_number >= MAX_WARNINGS:
            await self._terminate(session, f"{violation_type}: {reason or 'maximum warnings'}")
        await self.db.flush()
        return session

    async def admin_terminate_session(self, session: ExamSession, reason: str, actor_id: str) -> ExamSession:
        """Force terminate an active session by an Admin."""
        self.db.add(
            ViolationRecord(
                session_id=session.id,
                violation_type="ADMIN_TERMINATION",
                warning_number=session.warning_count + 1,
                reason=f"Admin termination by #{actor_id}: {reason}",
                ip_address=session.ip_address,
                user_agent=session.user_agent,
                device_fingerprint=session.device_fingerprint,
            )
        )
        await self._terminate(session, f"ADMIN_TERMINATION: {reason}")
        await self.db.flush()
        return session

    async def submit(self, session: ExamSession) -> ExamSession:
        if session.status != SessionStatus.ACTIVE:
            raise ValidationError("Session is not active", details={"code": "session_not_active"})
        session.status = SessionStatus.SUBMITTED
        session.submitted_at = datetime.now(UTC)
        session.time_spent_seconds = int((session.submitted_at - session.started_at).total_seconds())
        await self.db.flush()
        return session

    async def _expire(self, session: ExamSession) -> None:
        session.status = SessionStatus.EXPIRED
        session.submitted_at = datetime.now(UTC)
        session.time_spent_seconds = int((session.submitted_at - session.started_at).total_seconds())

    async def _terminate(self, session: ExamSession, reason: str) -> None:
        session.status = SessionStatus.TERMINATED
        session.terminated_at = datetime.now(UTC)
        session.terminate_reason = reason
        session.is_locked = True  # no future attempts ever

    async def get_active_session_for_student(self, student: Student, exam_id: str) -> ExamSession | None:
        result = await self.db.execute(
            select(ExamSession).where(
                ExamSession.student_id == student.id,
                ExamSession.exam_id == exam_id,
                ExamSession.status == SessionStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()