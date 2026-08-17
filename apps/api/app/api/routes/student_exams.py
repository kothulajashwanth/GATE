from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import require_roles
from app.core.errors import NotFoundError
from app.db.models.exam import Exam, ExamSchedule, ExamStatus
from app.db.models.session import ExamSession, SessionStatus
from app.db.models.student import Student
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.pagination import PaginatedResponse

from pydantic import BaseModel

router = APIRouter()


class StudentProfileOut(BaseModel):
    id: str
    rollNumber: str
    firstName: str
    lastName: str
    email: str
    phone: str | None = None
    department: dict | None = None
    semester: dict | None = None
    section: dict | None = None


@router.get("/profile", response_model=StudentProfileOut, summary="Get student profile details")
async def get_student_profile(
    user: Annotated[User, Depends(require_roles(Role.STUDENT, Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StudentProfileOut:
    student = await _student_or_404(db, user.id)
    res = await db.execute(
        select(Student)
        .where(Student.id == student.id)
        .options(
            selectinload(Student.department),
            selectinload(Student.semester),
            selectinload(Student.section),
            selectinload(Student.user),
        )
    )
    st = res.scalar_one()
    return StudentProfileOut(
        id=str(st.id),
        rollNumber=st.roll_number,
        firstName=st.first_name,
        lastName=st.last_name,
        email=st.email,
        phone=st.phone,
        department={"id": str(st.department.id), "name": st.department.name} if st.department else None,
        semester={"id": str(st.semester.id), "name": st.semester.name} if st.semester else None,
        section={"id": str(st.section.id), "name": st.section.name} if st.section else None,
    )


def _exam_preview(exam: Exam) -> dict:
    return {
        "id": str(exam.id),
        "title": exam.title,
        "subject": {"name": exam.subject.name} if getattr(exam, "subject", None) else None,
        "startAt": exam.start_at.isoformat() if exam.start_at else "",
        "endAt": exam.end_at.isoformat() if exam.end_at else "",
        "durationMinutes": exam.duration_minutes,
        "status": exam.status.value if hasattr(exam.status, "value") else str(exam.status),
    }


async def _student_or_404(db: AsyncSession, user_id) -> Student:
    result = await db.execute(select(Student).where(Student.user_id == user_id))
    student = result.scalar_one_or_none()
    if student is None:
        user_res = await db.execute(select(User).where(User.id == user_id))
        user = user_res.scalar_one_or_none()
        student = Student(
            user_id=user_id,
            roll_number=f"STU-{str(user_id)[:8].upper()}",
        )
        db.add(student)
        await db.commit()
        await db.refresh(student)
    return student


@router.get("/upcoming", response_model=PaginatedResponse[dict], summary="Student upcoming exams")
async def student_upcoming_exams(
    user: Annotated[User, Depends(require_roles(Role.STUDENT, Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[dict]:
    now_naive = datetime.now(UTC).replace(tzinfo=None)
    await _student_or_404(db, user.id)

    base = (
        select(Exam)
        .options(selectinload(Exam.subject))
        .where(
            or_(
                Exam.status == ExamStatus.PUBLISHED,
                Exam.status == ExamStatus.SCHEDULED,
                Exam.status == ExamStatus.LIVE,
            ),
            or_(Exam.end_at > now_naive, Exam.end_at.is_(None)),
            Exam.deleted_at.is_(None),
        )
        .order_by(Exam.start_at)
    )
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    result = await db.execute(base.limit(page_size).offset((page - 1) * page_size))
    items = [_exam_preview(e) for e in result.scalars().all()]
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(items=items, page=page, pageSize=page_size, total=total, totalPages=total_pages)


@router.get("/completed", response_model=PaginatedResponse[dict], summary="Student completed exams")
async def student_completed_exams(
    user: Annotated[User, Depends(require_roles(Role.STUDENT, Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[dict]:
    student = await _student_or_404(db, user.id)
    base = (
        select(Exam)
        .join(ExamSession, ExamSession.exam_id == Exam.id)
        .where(
            ExamSession.student_id == student.id,
            ExamSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.EXPIRED]),
            Exam.deleted_at.is_(None),
        )
        .distinct()
        .order_by(Exam.end_at.desc())
    )
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    result = await db.execute(base.limit(page_size).offset((page - 1) * page_size))
    items = [_exam_preview(e) for e in result.scalars().all()]
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(items=items, page=page, pageSize=page_size, total=total, totalPages=total_pages)