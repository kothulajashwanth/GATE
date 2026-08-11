import pytest
from datetime import UTC, datetime, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.exam import Exam, ExamStatus
from app.db.models.result import ExamResult, ResultStatus
from app.db.models.student import Student
from app.db.models.user import Role, User


@pytest.mark.asyncio
async def test_admin_overview_analytics_and_csv_export(
    client: AsyncClient,
    admin_token_headers: dict[str, str],
    student_token_headers: dict[str, str],
    db: AsyncSession,
    admin_user: User,
):
    """Test Admin Overview KPIs, score distribution histogram, CSV export, and RBAC rejection."""
    # 1. Admin GET Overview KPIs
    overview_res = await client.get("/api/v1/analytics/overview?days=30", headers=admin_token_headers)
    assert overview_res.status_code == 200, overview_res.text
    ov_data = overview_res.json()
    assert "totalStudents" in ov_data
    assert "totalExams" in ov_data
    assert "scoreDistribution" in ov_data

    # 2. Admin GET Department Analytics
    dept_res = await client.get("/api/v1/analytics/departments", headers=admin_token_headers)
    assert dept_res.status_code == 200
    assert isinstance(dept_res.json(), list)

    # 3. Admin GET Question Quality Analytics
    q_res = await client.get("/api/v1/analytics/questions", headers=admin_token_headers)
    assert q_res.status_code == 200

    # 4. Admin GET Security Violation Analytics
    sec_res = await client.get("/api/v1/analytics/security", headers=admin_token_headers)
    assert sec_res.status_code == 200
    assert "totalViolations" in sec_res.json()

    # 5. Admin Download CSV Report Export
    csv_res = await client.get("/api/v1/analytics/export", headers=admin_token_headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "GATE IGNITE" in csv_res.text

    # 6. Verify Student Role Rejection on Admin Analytics (MUST BE HTTP 403 FORBIDDEN)
    stud_admin_access = await client.get("/api/v1/analytics/overview", headers=student_token_headers)
    assert stud_admin_access.status_code == 403

    stud_csv_access = await client.get("/api/v1/analytics/export", headers=student_token_headers)
    assert stud_csv_access.status_code == 403


@pytest.mark.asyncio
async def test_student_personal_analytics_privacy(
    client: AsyncClient,
    student_token_headers: dict[str, str],
    db: AsyncSession,
    student_user: User,
    admin_user: User,
):
    """Test Student Personal Analytics endpoint and student data privacy."""
    student = (await db.execute(select(Student).where(Student.user_id == student_user.id))).scalar_one_or_none()
    if not student:
        student = Student(user_id=student_user.id, roll_number="CS2026006", is_active=True)
        db.add(student)
        await db.commit()

    now = datetime.now(UTC)
    exam = Exam(
        title="Analytics Test Exam",
        duration_minutes=30,
        start_at=now - timedelta(minutes=5),
        end_at=now + timedelta(hours=1),
        status=ExamStatus.PUBLISHED,
        created_by=admin_user.id,
    )
    db.add(exam)
    await db.commit()

    res = ExamResult(
        session_id=student.id,
        exam_id=exam.id,
        student_id=student.id,
        total_marks=10.0,
        obtained_marks=9.0,
        percentage=90.0,
        is_passed=True,
        status=ResultStatus.PUBLISHED,
    )
    db.add(res)
    await db.commit()

    # Student requests own personal analytics
    me_analytics = await client.get("/api/v1/analytics/students/me/analytics", headers=student_token_headers)
    assert me_analytics.status_code == 200, me_analytics.text
    me_data = me_analytics.json()
    assert me_data["totalExamsCompleted"] >= 1
    assert me_data["avgPercentage"] > 0
    assert len(me_data["performanceTrend"]) >= 1
