from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.errors import NotFoundError
from app.db.models.exam import Exam
from app.db.models.result import ExamResult, ResultStatus
from app.db.models.student import Student
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.result import ResultOut

router = APIRouter()


def _result_out(r: ExamResult) -> ResultOut:
    return ResultOut(
        id=str(r.id),
        examId=str(r.exam_id),
        examTitle=r.exam.title if r.exam else None,
        totalMarks=r.total_marks,
        obtainedMarks=r.obtained_marks,
        percentage=r.percentage,
        rank=r.rank,
        isPassed=r.is_passed,
        status=r.status.value,
        publishedAt=r.published_at,
        questionAnalysis=r.question_analysis,
    )


@router.get("", response_model=PaginatedResponse[ResultOut], summary="My results")
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
        .where(ExamResult.student_id == student.id, Exam.deleted_at.is_(None))
        .order_by(ExamResult.created_at.desc())
    )
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    result = await db.execute(base.limit(page_size).offset((page - 1) * page_size))
    items = [_result_out(r) for r in result.scalars().all()]
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(items=items, page=page, pageSize=page_size, total=total, totalPages=total_pages)