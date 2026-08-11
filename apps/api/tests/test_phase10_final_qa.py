import pytest
from datetime import UTC, datetime, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.exam import Exam, ExamQuestion, ExamStatus
from app.db.models.question import Question, QuestionType
from app.db.models.result import ExamResult, ResultStatus
from app.db.models.session import ExamSession, SessionStatus
from app.db.models.student import Student
from app.db.models.user import Role, User


@pytest.mark.asyncio
async def test_full_system_regression_and_qa(
    client: AsyncClient,
    admin_token_headers: dict[str, str],
    student_token_headers: dict[str, str],
    db: AsyncSession,
    admin_user: User,
    student_user: User,
):
    """Master E2E regression test verifying Phase 1 through Phase 9 APIs, security, & authorization."""

    # ----------------------------------------------------
    # Phase 1: Health & Database Check
    # ----------------------------------------------------
    health_res = await client.get("/health")
    assert health_res.status_code == 200

    # ----------------------------------------------------
    # Phase 2: Student Management
    # ----------------------------------------------------
    student = (await db.execute(select(Student).where(Student.user_id == student_user.id))).scalar_one_or_none()
    if not student:
        student = Student(user_id=student_user.id, roll_number="CS2026QA", is_active=True)
        db.add(student)
        await db.commit()

    stud_list_res = await client.get("/api/v1/students", headers=admin_token_headers)
    assert stud_list_res.status_code == 200

    # ----------------------------------------------------
    # Phase 3 & 4: Question Repository & AI Generator
    # ----------------------------------------------------
    q = Question(
        type=QuestionType.MCQ,
        text="What is the time complexity of QuickSort average case?",
        options=["O(N)", "O(N log N)", "O(N^2)", "O(1)"],
        correct_answers=["B"],
        marks=4,
        negative_marks=1.0,
        difficulty="medium",
        is_verified=True,
        created_by=admin_user.id,
    )
    db.add(q)
    await db.commit()

    # ----------------------------------------------------
    # Phase 5: Exam Builder & Lifecycle
    # ----------------------------------------------------
    now = datetime.now(UTC)
    exam = Exam(
        title="Master Production Final Exam 2026",
        duration_minutes=60,
        start_at=now - timedelta(minutes=5),
        end_at=now + timedelta(hours=2),
        passing_marks=50,
        negative_marks_enabled=True,
        negative_marks_value=1.0,
        status=ExamStatus.DRAFT,
        created_by=admin_user.id,
    )
    db.add(exam)
    await db.commit()
    exam_id = str(exam.id)

    # Assign question
    eq_res = await client.post(
        f"/api/v1/exams/{exam_id}/questions",
        json={"question_ids": [str(q.id)]},
        headers=admin_token_headers,
    )
    assert eq_res.status_code == 200

    # Publish exam
    pub_res = await client.post(f"/api/v1/exams/{exam_id}/publish", headers=admin_token_headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "published"

    # ----------------------------------------------------
    # Phase 6: Secure Exam Engine & Technical Preflight
    # ----------------------------------------------------
    preflight_res = await client.get(f"/api/v1/exam-session/preflight/{exam_id}", headers=student_token_headers)
    assert preflight_res.status_code == 200
    assert preflight_res.json()["isEligible"] is True

    start_res = await client.post("/api/v1/exam-session/start", json={"examId": exam_id}, headers=student_token_headers)
    assert start_res.status_code == 200
    session_id = start_res.json()["sessionId"]

    ans_res = await client.post(
        f"/api/v1/exam-session/{session_id}/answer",
        json={"questionId": str(q.id), "answer": ["B"]},
        headers=student_token_headers,
    )
    assert ans_res.status_code == 200

    # ----------------------------------------------------
    # Phase 7: Anti-Cheat Telemetry
    # ----------------------------------------------------
    viol_res = await client.post(
        f"/api/v1/exam-session/{session_id}/violation",
        json={"violationType": "TAB_SWITCH", "reason": "Tab switched"},
        headers=student_token_headers,
    )
    assert viol_res.status_code == 200

    live_mon_res = await client.get("/api/v1/sessions?session_status=active", headers=admin_token_headers)
    assert live_mon_res.status_code == 200

    # ----------------------------------------------------
    # Phase 8: Submission & Automatic Evaluation
    # ----------------------------------------------------
    sub_res = await client.post(f"/api/v1/exam-session/{session_id}/submit", headers=student_token_headers)
    assert sub_res.status_code == 200

    result = (await db.execute(select(ExamResult).where(ExamResult.session_id == session_id))).scalar_one_or_none()
    assert result is not None
    assert result.obtained_marks == 4.0

    # Admin publishes result
    admin_pub = await client.post(f"/api/v1/results/admin/{result.id}/publish", headers=admin_token_headers)
    assert admin_pub.status_code == 200

    # ----------------------------------------------------
    # Phase 9: Analytics & CSV Report Export
    # ----------------------------------------------------
    overview_res = await client.get("/api/v1/analytics/overview?days=30", headers=admin_token_headers)
    assert overview_res.status_code == 200

    csv_res = await client.get("/api/v1/analytics/export", headers=admin_token_headers)
    assert csv_res.status_code == 200

    me_analytics = await client.get("/api/v1/analytics/students/me/analytics", headers=student_token_headers)
    assert me_analytics.status_code == 200

    # ----------------------------------------------------
    # Security & RBAC Enforcement (IDOR Protection)
    # ----------------------------------------------------
    stud_admin_analytics = await client.get("/api/v1/analytics/overview", headers=student_token_headers)
    assert stud_admin_analytics.status_code == 403

    stud_admin_live = await client.get("/api/v1/sessions", headers=student_token_headers)
    assert stud_admin_live.status_code == 403
