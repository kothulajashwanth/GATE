from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.errors import BadRequestError, ForbiddenError, NotFoundError
from app.db.models.exam import Exam
from app.db.models.result import ExamResult, ResultStatus
from app.db.models.student import Student
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.result import ResultOut
from app.services.audit import AuditService
from app.services.results import ResultCalculator

router = APIRouter()


class ManualGradeRequest(BaseModel):
    questionId: str
    awardedMarks: float = Field(ge=0)
    comments: str | None = None


class WithholdRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


def _result_out(r: ExamResult, student: Student | None = None) -> ResultOut:
    return ResultOut(
        id=str(r.id),
        examId=str(r.exam_id),
        examTitle=r.exam.title if r.exam else None,
        studentRollNumber=student.roll_number if student else None,
        studentName=student.user.full_name if (student and student.user) else None,
        totalMarks=r.total_marks,
        obtainedMarks=r.obtained_marks,
        percentage=r.percentage,
        rank=r.rank,
        isPassed=r.is_passed,
        status=r.status.value,
        publishedAt=r.published_at,
        questionAnalysis=r.question_analysis,
    )


@router.get("/me", response_model=PaginatedResponse[ResultOut], summary="My published results")
async def my_results(
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[ResultOut]:
    student_result = await db.execute(select(Student).where(Student.user_id == user.id))
    student = student_result.scalar_one_or_none()
    if student is None:
        raise NotFoundError("Student profile not found")

    base = (
        select(ExamResult)
        .join(Exam, ExamResult.exam_id == Exam.id)
        .where(
            ExamResult.student_id == student.id,
            ExamResult.status == ResultStatus.PUBLISHED,
            Exam.deleted_at.is_(None),
        )
        .order_by(ExamResult.created_at.desc())
    )
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    result = await db.execute(base.limit(page_size).offset((page - 1) * page_size))
    items = [_result_out(r, student) for r in result.scalars().all()]
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(items=items, page=page, pageSize=page_size, total=total, totalPages=total_pages)


@router.get("/me/{result_id}", response_model=ResultOut, summary="My result detail breakdown")
async def my_result_detail(
    result_id: str,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResultOut:
    student_result = await db.execute(select(Student).where(Student.user_id == user.id))
    student = student_result.scalar_one_or_none()
    if student is None:
        raise NotFoundError("Student profile not found")

    result = (await db.execute(select(ExamResult).where(ExamResult.id == result_id))).scalar_one_or_none()
    if not result or result.student_id != student.id:
        raise ForbiddenError("Not authorized to view this result")
    if result.status != ResultStatus.PUBLISHED:
        raise ForbiddenError("Result is not published yet")

    return _result_out(result, student)


@router.get("/admin", response_model=PaginatedResponse[ResultOut], summary="Admin list results")
async def admin_list_results(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
    exam_id: str | None = None,
    result_status: str | None = None,
) -> PaginatedResponse[ResultOut]:
    base = select(ExamResult).order_by(ExamResult.created_at.desc())
    if exam_id:
        base = base.where(ExamResult.exam_id == exam_id)
    if result_status and result_status != "all":
        try:
            base = base.where(ExamResult.status == ResultStatus(result_status))
        except ValueError:
            pass

    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    res = await db.execute(base.limit(page_size).offset((page - 1) * page_size))
    results = res.scalars().all()

    items = []
    for r in results:
        student = (await db.execute(select(Student).where(Student.id == r.student_id))).scalar_one_or_none()
        items.append(_result_out(r, student))

    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(items=items, page=page, pageSize=page_size, total=total, totalPages=total_pages)


@router.post("/admin/{result_id}/publish", response_model=ResultOut, summary="Publish single student result")
async def publish_single_result(
    result_id: str,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResultOut:
    result = (await db.execute(select(ExamResult).where(ExamResult.id == result_id))).scalar_one_or_none()
    if not result:
        raise NotFoundError("Result not found")

    result.status = ResultStatus.PUBLISHED
    result.published_at = datetime.now(UTC)
    await db.flush()

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="RESULT_PUBLISHED",
        entity_type="exam_result",
        entity_id=result_id,
        new_value={"status": "published"},
    )
    await db.commit()

    student = (await db.execute(select(Student).where(Student.id == result.student_id))).scalar_one_or_none()
    return _result_out(result, student)


@router.post("/admin/exams/{exam_id}/publish-all", summary="Batch publish all evaluated results for an exam")
async def publish_all_exam_results(
    exam_id: str,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    calc = ResultCalculator(db)
    await calc.publish_results(exam_id)

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="EXAM_RESULTS_BATCH_PUBLISHED",
        entity_type="exam",
        entity_id=exam_id,
        new_value={"status": "published"},
    )
    await db.commit()
    return {"status": "SUCCESS", "message": "All evaluated results published successfully"}


@router.post("/admin/{result_id}/recalculate", response_model=ResultOut, summary="Recalculate result score snapshot")
async def recalculate_result(
    result_id: str,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResultOut:
    result = (await db.execute(select(ExamResult).where(ExamResult.id == result_id))).scalar_one_or_none()
    if not result:
        raise NotFoundError("Result not found")

    calc = ResultCalculator(db)
    session_res = await db.execute(select(ExamResult.session_id).where(ExamResult.id == result_id))
    session_id = session_res.scalar_one()

    from app.db.models.session import ExamSession

    session = (await db.execute(select(ExamSession).where(ExamSession.id == session_id))).scalar_one()
    updated_result = await calc.evaluate_session(session)

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="RESULT_RECALCULATED",
        entity_type="exam_result",
        entity_id=result_id,
        new_value={"obtained_marks": updated_result.obtained_marks, "percentage": updated_result.percentage},
    )
    await db.commit()

    student = (await db.execute(select(Student).where(Student.id == result.student_id))).scalar_one_or_none()
    return _result_out(updated_result, student)