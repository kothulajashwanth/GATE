from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import require_roles
from app.db.models.exam import Exam
from app.db.models.result import ExamResult
from app.db.models.session import ExamSession
from app.db.models.student import Student
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.pagination import PaginatedResponse
from app.schemas.result import ResultOut

router = APIRouter()


@router.get("/exam/{exam_id}/results", response_model=PaginatedResponse[ResultOut], summary="Exam results (admin)")
async def exam_results(
    exam_id: str,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[ResultOut]:
    from app.schemas.pagination import PaginatedResponse as PR
    base = select(ExamResult).where(ExamResult.exam_id == exam_id).order_by(ExamResult.obtained_marks.desc())
    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    result = await db.execute(base.limit(page_size).offset((page - 1) * page_size))
    items = [ResultOut.model_validate(r, from_attributes=True) for r in result.scalars().all()]
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PR(items=items, page=page, pageSize=page_size, total=total, totalPages=total_pages)


@router.get("/exam/{exam_id}/analytics", summary="Exam analytics: score distribution, time analysis, question analysis")
async def exam_analytics(
    exam_id: str,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    # Score stats
    stats = await db.execute(
        select(
            func.count(ExamResult.id),
            func.avg(ExamResult.percentage),
            func.min(ExamResult.percentage),
            func.max(ExamResult.percentage),
            func.stddev_pop(ExamResult.percentage),
        ).where(ExamResult.exam_id == exam_id)
    )
    count, avg_pct, min_pct, max_pct, std_pct = stats.one()

    # Score distribution (bins)
    bins = await db.execute(
        select(
            func.floor(ExamResult.percentage / 10) * 10,
            func.count(),
        ).where(ExamResult.exam_id == exam_id).group_by(func.floor(ExamResult.percentage / 10) * 10).order_by(func.floor(ExamResult.percentage / 10) * 10)
    )
    score_dist = [{"range": f"{int(bin_)}–{int(bin_)+9}", "count": c} for bin_, c in bins.all()]

    # Time analysis: average time spent
    time_stats = await db.execute(
        select(
            func.avg(ExamSession.time_spent_seconds),
            func.min(ExamSession.time_spent_seconds),
            func.max(ExamSession.time_spent_seconds),
        ).where(ExamSession.exam_id == exam_id, ExamSession.status.in_(["submitted", "expired"]))
    )
    avg_time, min_time, max_time = time_stats.one()

    # Question-level analysis
    from app.db.models.exam import ExamQuestion
    from app.db.models.question import Question
    from app.db.models.session import SessionAnswer

    q_analysis = await db.execute(
        select(
            Question.id,
            Question.text,
            Question.type,
            func.count(SessionAnswer.id).label("total"),
            func.sum(func.cast(SessionAnswer.is_answered, int)).label("answered"),
            func.sum(func.cast(SessionAnswer.is_correct, int)).label("correct"),
            func.avg(SessionAnswer.marks_awarded).label("avg_marks"),
        )
        .select_from(ExamQuestion)
        .join(Question, ExamQuestion.question_id == Question.id)
        .outerjoin(SessionAnswer, SessionAnswer.question_id == Question.id)
        .where(ExamQuestion.exam_id == ExamQuestion.exam_id, ExamQuestion.exam_id == exam_id)
        .group_by(Question.id, Question.text, Question.type)
        .order_by(ExamQuestion.order_index)
    )
    question_analysis = [
        {
            "questionId": str(row.id),
            "text": row.text[:80] + "..." if len(row.text) > 80 else row.text,
            "type": row.type.value,
            "totalAttempts": row.total,
            "answered": row.answered or 0,
            "correct": row.correct or 0,
            "accuracy": round((row.correct or 0) / (row.answered or 1) * 100, 1),
            "avgMarks": round(row.avg_marks or 0, 2),
        }
        for row in q_analysis.all()
    ]

    # Department/semester breakdown
    from app.db.models.student import Student
    from app.db.models.academic import Department, Semester, Section

    dept_breakdown = await db.execute(
        select(
            Department.name,
            func.count(ExamResult.id),
            func.avg(ExamResult.percentage),
        )
        .join(Student, ExamResult.student_id == Student.id)
        .join(Department, Student.department_id == Department.id)
        .where(ExamResult.exam_id == exam_id)
        .group_by(Department.name)
    )
    dept_stats = [
        {"department": d, "count": c, "avgPercentage": round(float(a) if a else 0, 1)}
        for d, c, a in dept_breakdown.all()
    ]

    sem_breakdown = await db.execute(
        select(
            Semester.name,
            func.count(ExamResult.id),
            func.avg(ExamResult.percentage),
        )
        .join(Student, ExamResult.student_id == Student.id)
        .join(Semester, Student.semester_id == Semester.id)
        .where(ExamResult.exam_id == exam_id)
        .group_by(Semester.name)
    )
    sem_stats = [
        {"semester": s, "count": c, "avgPercentage": round(float(a) if a else 0, 1)}
        for s, c, a in sem_breakdown.all()
    ]

    return {
        "examId": exam_id,
        "scoreStats": {
            "count": count or 0,
            "avgPercentage": round(float(avg_pct) if avg_pct else 0, 1),
            "minPercentage": round(float(min_pct) if min_pct else 0, 1),
            "maxPercentage": round(float(max_pct) if max_pct else 0, 1),
            "stdPercentage": round(float(std_pct) if std_pct else 0, 1),
        },
        "scoreDistribution": score_dist,
        "timeStats": {
            "avgTimeSeconds": round(avg_time or 0),
            "minTimeSeconds": min_time or 0,
            "maxTimeSeconds": max_time or 0,
        },
        "questionAnalysis": question_analysis,
        "departmentBreakdown": dept_stats,
        "semesterBreakdown": sem_stats,
    }


@router.get("/exam/{exam_id}/report", summary="Download exam report (pdf/excel/csv)")
async def exam_report(
    exam_id: str,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: str = "pdf",
) -> StreamingResponse:
    from app.services.reports import generate_pdf, generate_excel, generate_csv

    result = await db.execute(
        select(ExamResult)
        .where(ExamResult.exam_id == exam_id)
        .options(selectinload(ExamResult.student).selectinload(Student.user),
                 selectinload(ExamResult.student).selectinload(Student.department),
                 selectinload(ExamResult.student).selectinload(Student.semester))
    )
    results = list(result.scalars().all())
    exam = await db.execute(select(Exam).where(Exam.id == exam_id))
    exam_title = exam.scalar_one_or_none().title if exam.scalar_one_or_none() else "Exam"

    if format == "pdf":
        buf = generate_pdf(exam_title, results)
        media = "application/pdf"
        ext = "pdf"
    elif format == "excel" or format == "xlsx":
        buf = generate_excel(exam_title, results)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    else:
        buf = generate_csv(exam_title, results)
        media = "text/csv"
        ext = "csv"

    return StreamingResponse(
        buf,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="report_{exam_id}.{ext}"'},
    )


@router.get("/department/{department_id}/analytics", summary="Department-wide analytics")
async def department_analytics(
    department_id: str,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    # Aggregate across all exams for this department
    from app.db.models.student import Student
    from app.db.models.exam import ExamSchedule

    overall = await db.execute(
        select(
            func.count(ExamResult.id),
            func.avg(ExamResult.percentage),
            func.avg(ExamResult.obtained_marks),
        )
        .join(Student, ExamResult.student_id == Student.id)
        .where(Student.department_id == department_id)
    )
    count, avg_pct, avg_marks = overall.one()

    # Per exam
    exams = await db.execute(
        select(
            Exam.id,
            Exam.title,
            func.count(ExamResult.id),
            func.avg(ExamResult.percentage),
        )
        .join(ExamResult, ExamResult.exam_id == Exam.id)
        .join(ExamSchedule, ExamSchedule.exam_id == Exam.id)
        .where(ExamSchedule.department_id == department_id)
        .group_by(Exam.id, Exam.title)
        .order_by(func.count(ExamResult.id).desc())
        .limit(20)
    )
    top_exams = [
        {"examId": str(e.id), "title": e.title, "attempts": c, "avgPercentage": round(float(a) if a else 0, 1)}
        for e, c, a in exams.all()
    ]

    # Subject analysis
    from app.db.models.question import Question, Subject

    subj = await db.execute(
        select(
            Subject.name,
            func.count(Question.id),
        )
        .join(Question, Question.subject_id == Subject.id)
        .where(Subject.department_id == department_id)
        .group_by(Subject.name)
    )
    subjects = [{"subject": s, "questionCount": c} for s, c in subj.all()]

    return {
        "departmentId": department_id,
        "totalResults": count or 0,
        "avgPercentage": round(float(avg_pct) if avg_pct else 0, 1),
        "avgMarks": round(float(avg_marks) if avg_marks else 0, 1),
        "topExams": top_exams,
        "subjects": subjects,
    }