from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.errors import BadRequestError, NotFoundError
from app.db.models.exam import Exam, ExamQuestion, ExamSchedule, ExamStatus
from app.db.models.question import Question
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.exam import ExamCreate, ExamOut, ExamUpdate
from app.schemas.pagination import PaginatedResponse
from app.services.audit import AuditService

router = APIRouter()

# Valid status transitions map
VALID_TRANSITIONS: dict[ExamStatus, set[ExamStatus]] = {
    ExamStatus.DRAFT: {ExamStatus.REVIEW, ExamStatus.SCHEDULED, ExamStatus.PUBLISHED, ExamStatus.CANCELLED},
    ExamStatus.REVIEW: {ExamStatus.SCHEDULED, ExamStatus.PUBLISHED, ExamStatus.CANCELLED},
    ExamStatus.SCHEDULED: {ExamStatus.PUBLISHED, ExamStatus.CANCELLED},
    ExamStatus.PUBLISHED: {ExamStatus.LIVE, ExamStatus.CANCELLED},
    ExamStatus.LIVE: {ExamStatus.COMPLETED, ExamStatus.CANCELLED},
    ExamStatus.COMPLETED: {ExamStatus.ARCHIVED},
    ExamStatus.CANCELLED: set(),
    ExamStatus.ARCHIVED: set(),
}


def _exam_out(exam: Exam) -> ExamOut:
    return ExamOut(
        id=str(exam.id),
        title=exam.title,
        description=exam.description,
        subjectId=str(exam.subject_id) if exam.subject_id else None,
        durationMinutes=exam.duration_minutes,
        startAt=exam.start_at,
        endAt=exam.end_at,
        passingMarks=exam.passing_marks,
        negativeMarksEnabled=exam.negative_marks_enabled,
        negativeMarksValue=exam.negative_marks_value,
        randomizeQuestions=exam.randomize_questions,
        shuffleOptions=exam.shuffle_options,
        attemptLimit=exam.attempt_limit,
        questionMode=exam.question_mode.value,
        instructions=exam.instructions,
        visibility=exam.visibility,
        status=exam.status.value,
        totalMarks=exam.total_marks,
        securityMode=exam.security_mode,
        cameraProctoringEnabled=exam.camera_proctoring_enabled,
        autoSubmit=exam.auto_submit,
        createdAt=exam.created_at,
        updatedAt=exam.updated_at,
    )


async def _get_exam_or_404(db: AsyncSession, exam_id: str) -> Exam:
    result = await db.execute(select(Exam).where(Exam.id == exam_id, Exam.deleted_at.is_(None)))
    exam = result.scalar_one_or_none()
    if exam is None:
        raise NotFoundError("Exam not found")
    return exam


class AssignQuestionsRequest(BaseModel):
    question_ids: list[str]
    marks_override: dict[str, int] | None = None


class ScheduleAssignRequest(BaseModel):
    department_id: str | None = None
    semester_id: str | None = None
    section_id: str | None = None


class CancelExamRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class StatusTransitionRequest(BaseModel):
    target_status: str = Field(pattern="^(draft|review|scheduled|published|live|completed|cancelled|archived)$")


@router.get("", response_model=PaginatedResponse[ExamOut], summary="List exams")
async def list_exams(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
    exam_status: str | None = None,
) -> PaginatedResponse[ExamOut]:
    base = select(Exam).where(Exam.deleted_at.is_(None)).order_by(Exam.created_at.desc())
    if exam_status and exam_status != "all":
        try:
            base = base.where(Exam.status == ExamStatus(exam_status))
        except ValueError:
            pass

    count_stmt = select(func.count()).select_from(base.subquery())
    total = int((await db.execute(count_stmt)).scalar_one())
    result = await db.execute(base.limit(page_size).offset((page - 1) * page_size))
    items = [_exam_out(e) for e in result.scalars().all()]
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(items=items, page=page, pageSize=page_size, total=total, totalPages=total_pages)


@router.get("/{exam_id}", response_model=ExamOut, summary="Exam detail")
async def get_exam(
    exam_id: str,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamOut:
    return _exam_out(await _get_exam_or_404(db, exam_id))


@router.post("", response_model=ExamOut, status_code=status.HTTP_201_CREATED, summary="Create exam draft")
async def create_exam(
    body: ExamCreate,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamOut:
    if body.startAt >= body.endAt:
        raise BadRequestError("Exam start time must be before end time")

    exam = Exam(
        title=body.title,
        description=body.description,
        subject_id=body.subjectId,
        created_by=actor.id,
        duration_minutes=body.durationMinutes,
        start_at=body.startAt,
        end_at=body.endAt,
        passing_marks=body.passingMarks,
        negative_marks_enabled=body.negativeMarksEnabled,
        negative_marks_value=body.negativeMarksValue,
        randomize_questions=body.randomizeQuestions,
        shuffle_options=body.shuffleOptions,
        attempt_limit=body.attemptLimit,
        question_mode=body.questionMode,
        instructions=body.instructions,
        visibility=body.visibility,
        status=ExamStatus.DRAFT,
        security_mode=body.securityMode,
        camera_proctoring_enabled=body.cameraProctoringEnabled,
        auto_submit=body.autoSubmit,
        total_marks=0,
    )
    db.add(exam)
    await db.flush()

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="EXAM_CREATED",
        entity_type="exam",
        entity_id=str(exam.id),
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    return _exam_out(exam)


@router.patch("/{exam_id}", response_model=ExamOut, summary="Update exam settings")
async def update_exam(
    exam_id: str,
    body: ExamUpdate,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamOut:
    exam = await _get_exam_or_404(db, exam_id)
    if exam.status in (ExamStatus.LIVE, ExamStatus.COMPLETED, ExamStatus.ARCHIVED):
        raise BadRequestError(f"Cannot modify exam in {exam.status.value} status")

    old_value = {"status": exam.status.value, "title": exam.title}
    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    for k, v in updates.items():
        setattr(exam, k, v)

    if exam.start_at >= exam.end_at:
        raise BadRequestError("Exam start time must be before end time")

    await db.flush()

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="EXAM_UPDATED",
        entity_type="exam",
        entity_id=str(exam.id),
        old_value=old_value,
        new_value=body.model_dump(mode="json", exclude_none=True),
    )
    await db.commit()
    return _exam_out(exam)


@router.post("/{exam_id}/questions", summary="Assign and reorder approved questions in exam")
async def assign_exam_questions(
    exam_id: str,
    body: AssignQuestionsRequest,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    exam = await _get_exam_or_404(db, exam_id)
    if exam.status in (ExamStatus.LIVE, ExamStatus.COMPLETED, ExamStatus.ARCHIVED):
        raise BadRequestError("Cannot alter questions for live or completed exam")

    # Clear existing question links
    existing_eqs = (await db.execute(select(ExamQuestion).where(ExamQuestion.exam_id == exam.id))).scalars().all()
    for eq in existing_eqs:
        await db.delete(eq)

    total_marks = 0
    assigned_ids = []
    overrides = body.marks_override or {}

    for order_idx, q_id in enumerate(body.question_ids, start=1):
        q = (await db.execute(select(Question).where(Question.id == q_id, Question.deleted_at.is_(None)))).scalar_one_or_none()
        if not q:
            continue
        if not q.is_verified:
            raise BadRequestError(f"Question #{q_id} is unapproved. Only approved questions can be added to exams.")

        q_marks = overrides.get(q_id, q.marks or 1)
        total_marks += q_marks

        eq = ExamQuestion(
            exam_id=exam.id,
            question_id=q.id,
            order_index=order_idx,
            marks=q_marks,
        )
        db.add(eq)
        assigned_ids.append(str(q.id))

    exam.total_marks = total_marks
    await db.flush()

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="EXAM_QUESTIONS_UPDATED",
        entity_type="exam",
        entity_id=str(exam.id),
        new_value={"assigned_count": len(assigned_ids), "total_marks": total_marks},
    )
    await db.commit()
    return {"status": "SUCCESS", "assigned_count": len(assigned_ids), "total_marks": total_marks}


@router.post("/{exam_id}/schedule", summary="Assign department/semester/section schedule to exam")
async def assign_exam_schedule(
    exam_id: str,
    body: ScheduleAssignRequest,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    exam = await _get_exam_or_404(db, exam_id)
    sched = ExamSchedule(
        exam_id=exam.id,
        department_id=body.department_id,
        semester_id=body.semester_id,
        section_id=body.section_id,
    )
    db.add(sched)
    await db.flush()

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="EXAM_SCHEDULED",
        entity_type="exam",
        entity_id=str(exam.id),
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    return {"status": "SUCCESS", "schedule_id": str(sched.id)}


@router.post("/{exam_id}/validate", summary="Comprehensive publish readiness validation")
async def validate_exam_readiness(
    exam_id: str,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    exam = await _get_exam_or_404(db, exam_id)
    eq_count = int((await db.execute(select(func.count(ExamQuestion.id)).where(ExamQuestion.exam_id == exam.id))).scalar_one())

    issues = []
    if not exam.title or len(exam.title) < 3:
        issues.append("Exam title must be at least 3 characters long")
    if eq_count == 0:
        issues.append("Exam must contain at least 1 question")
    if exam.start_at >= exam.end_at:
        issues.append("Start time must be strictly before end time")
    if (exam.end_at - exam.start_at).total_seconds() / 60 < exam.duration_minutes:
        issues.append(f"Available window is smaller than requested duration ({exam.duration_minutes} mins)")
    if exam.passing_marks > exam.total_marks:
        issues.append("Passing marks cannot exceed total exam marks")

    is_ready = len(issues) == 0
    return {
        "exam_id": str(exam.id),
        "is_ready": is_ready,
        "question_count": eq_count,
        "total_marks": exam.total_marks,
        "issues": issues,
    }


@router.post("/{exam_id}/publish", response_model=ExamOut, summary="Publish exam to students")
async def publish_exam(
    exam_id: str,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamOut:
    exam = await _get_exam_or_404(db, exam_id)
    if exam.status in (ExamStatus.PUBLISHED, ExamStatus.LIVE, ExamStatus.COMPLETED):
        raise BadRequestError(f"Exam is already in {exam.status.value} status")

    eq_count = int((await db.execute(select(func.count(ExamQuestion.id)).where(ExamQuestion.exam_id == exam.id))).scalar_one())
    if eq_count == 0:
        raise BadRequestError("Cannot publish exam without questions")

    exam.status = ExamStatus.PUBLISHED
    await db.flush()

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="EXAM_PUBLISHED",
        entity_type="exam",
        entity_id=str(exam.id),
        new_value={"status": "published", "question_count": eq_count},
    )
    await db.commit()
    return _exam_out(exam)


@router.post("/{exam_id}/transition", response_model=ExamOut, summary="Transition exam lifecycle status")
async def transition_exam_status(
    exam_id: str,
    body: StatusTransitionRequest,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamOut:
    exam = await _get_exam_or_404(db, exam_id)
    target = ExamStatus(body.target_status.lower())

    if target not in VALID_TRANSITIONS.get(exam.status, set()):
        raise BadRequestError(f"Invalid transition from {exam.status.value} to {target.value}")

    old_status = exam.status.value
    exam.status = target
    await db.flush()

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="EXAM_STATUS_TRANSITION",
        entity_type="exam",
        entity_id=str(exam.id),
        old_value={"status": old_status},
        new_value={"status": target.value},
    )
    await db.commit()
    return _exam_out(exam)


@router.post("/{exam_id}/cancel", response_model=ExamOut, summary="Cancel an exam")
async def cancel_exam(
    exam_id: str,
    body: CancelExamRequest,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamOut:
    exam = await _get_exam_or_404(db, exam_id)
    if exam.status in (ExamStatus.COMPLETED, ExamStatus.ARCHIVED):
        raise BadRequestError(f"Cannot cancel exam in {exam.status.value} status")

    old_status = exam.status.value
    exam.status = ExamStatus.CANCELLED
    await db.flush()

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="EXAM_CANCELLED",
        entity_type="exam",
        entity_id=str(exam.id),
        old_value={"status": old_status},
        new_value={"reason": body.reason, "status": "cancelled"},
    )
    await db.commit()
    return _exam_out(exam)


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete exam (soft)")
async def delete_exam(
    exam_id: str,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    exam = await _get_exam_or_404(db, exam_id)
    if exam.status in (ExamStatus.PUBLISHED, ExamStatus.LIVE, ExamStatus.COMPLETED):
        raise BadRequestError(f"Cannot delete exam in {exam.status.value} status. Use cancel or archive instead.")

    exam.deleted_at = datetime.now(UTC)
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="EXAM_DELETED",
        entity_type="exam",
        entity_id=exam_id,
        old_value={"title": exam.title},
    )
    await db.commit()