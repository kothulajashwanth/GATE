from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import require_roles
from app.core.errors import NotFoundError
from app.db.models.exam import Exam, ExamStatus
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.exam import ExamCreate, ExamOut, ExamUpdate
from app.schemas.pagination import PaginatedResponse
from app.services.audit import AuditService

router = APIRouter()


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


@router.get("", response_model=PaginatedResponse[ExamOut], summary="List exams")
async def list_exams(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
    exam_status: str | None = None,
) -> PaginatedResponse[ExamOut]:
    base = select(Exam).where(Exam.deleted_at.is_(None)).order_by(Exam.created_at.desc())
    if exam_status:
        base = base.where(Exam.status == ExamStatus(exam_status))
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


@router.post("", response_model=ExamOut, status_code=status.HTTP_201_CREATED, summary="Create exam")
async def create_exam(
    body: ExamCreate,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamOut:
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
        action="exam.create",
        entity_type="exam",
        entity_id=str(exam.id),
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    return _exam_out(exam)


@router.patch("/{exam_id}", response_model=ExamOut, summary="Update exam")
async def update_exam(
    exam_id: str,
    body: ExamUpdate,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExamOut:
    exam = await _get_exam_or_404(db, exam_id)
    old_value = {"status": exam.status.value}
    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    for k, v in updates.items():
        setattr(exam, k, v)
    await db.flush()
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="exam.update",
        entity_type="exam",
        entity_id=str(exam.id),
        old_value=old_value,
        new_value=body.model_dump(mode="json", exclude_none=True),
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
    exam.deleted_at = datetime.now(UTC)
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="exam.delete",
        entity_type="exam",
        entity_id=exam_id,
        old_value={"title": exam.title},
    )
    await db.commit()