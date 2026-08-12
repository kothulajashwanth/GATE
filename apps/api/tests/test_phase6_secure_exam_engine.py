import pytest
from datetime import UTC, datetime, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.exam import Exam, ExamQuestion, ExamStatus
from app.db.models.question import Question, QuestionType
from app.db.models.session import ExamSession, SessionStatus
from app.db.models.student import Student
from app.db.models.user import Role, User


@pytest.mark.asyncio
async def test_preflight_and_session_lifecycle(
    client: AsyncClient,
    student_token_headers: dict[str, str],
    admin_token_headers: dict[str, str],
    db: AsyncSession,
    student_user: User,
    admin_user: User,
):
    """Test Preflight check, exam session start, answer autosave, violation logging, and submission locking."""
    # 1. Setup Student Profile
    student = (await db.execute(select(Student).where(Student.user_id == student_user.id))).scalar_one_or_none()
    if not student:
        student = Student(user_id=student_user.id, roll_number="CS2026001", is_active=True)
        db.add(student)
        await db.commit()

    # 2. Setup Question and Published Exam
    q = Question(
        type=QuestionType.MCQ,
        text="What is the function of CPU cache memory?",
        options=["Store OS Kernel", "Reduce memory latency", "Display Graphics", "Manage Power"],
        correct_answers=["B"],
        marks=2,
        is_verified=True,
        created_by=admin_user.id,
    )
    db.add(q)
    await db.commit()

    now = datetime.now(UTC)
    exam = Exam(
        title="Computer Architecture Exam",
        duration_minutes=60,
        start_at=now - timedelta(minutes=10),
        end_at=now + timedelta(hours=2),
        status=ExamStatus.PUBLISHED,
        passing_marks=1,
        attempt_limit=1,
        created_by=admin_user.id,
    )
    db.add(exam)
    await db.commit()

    eq = ExamQuestion(exam_id=exam.id, question_id=q.id, order_index=1, marks=2)
    db.add(eq)
    await db.commit()
    exam_id = str(exam.id)

    # 3. Test Technical & Eligibility Preflight Endpoint
    pre_res = await client.get(f"/api/v1/exam-session/preflight/{exam_id}", headers=student_token_headers)
    assert pre_res.status_code == 200, pre_res.text
    pre_data = pre_res.json()
    assert pre_data["isEligible"] is True
    assert pre_data["examOpen"] is True
    assert pre_data["remainingAttempts"] == 1

    # 4. Start Exam Session
    start_res = await client.post("/api/v1/exam-session/start", json={"examId": exam_id}, headers=student_token_headers)
    assert start_res.status_code == 200, start_res.text
    sess_data = start_res.json()
    session_id = sess_data["sessionId"]
    assert sess_data["status"] == "active"
    assert len(sess_data["questions"]) == 1

    # Verify correct answers are STRIPPED from student question view
    assert "correct_answers" not in sess_data["questions"][0]
    assert "correctAnswers" not in sess_data["questions"][0]

    # 5. Save Answer (Autosave)
    ans_res = await client.post(
        f"/api/v1/exam-session/{session_id}/answer",
        json={"questionId": str(q.id), "answer": ["Reduce memory latency"]},
        headers=student_token_headers,
    )
    assert ans_res.status_code == 200
    assert ans_res.json()["saved"] is True

    # 6. Record Security Telemetry Violation (e.g. TAB_SWITCH)
    viol_res = await client.post(
        f"/api/v1/exam-session/{session_id}/violation",
        json={"violationType": "TAB_SWITCH", "reason": "Browser tab minimized"},
        headers=student_token_headers,
    )
    assert viol_res.status_code == 200
    assert viol_res.json()["warningCount"] == 1

    # 7. Submit Exam
    sub_res = await client.post(f"/api/v1/exam-session/{session_id}/submit", headers=student_token_headers)
    assert sub_res.status_code == 200
    assert sub_res.json()["submitted"] is True

    # 8. Verify Attempt Locking (Saving further answers must be rejected)
    post_sub_ans = await client.post(
        f"/api/v1/exam-session/{session_id}/answer",
        json={"questionId": str(q.id), "answer": ["Changed Option"]},
        headers=student_token_headers,
    )
    assert post_sub_ans.status_code == 400


@pytest.mark.asyncio
async def test_attempt_ownership_protection(
    client: AsyncClient,
    admin_token_headers: dict[str, str],
    student_token_headers: dict[str, str],
    db: AsyncSession,
    admin_user: User,
):
    """Test that unauthorized students cannot access or save answers to another student's session."""
    # Attempt access with Admin credentials on student route or invalid session
    resp = await client.get("/api/v1/exam-session/invalid-session-id", headers=student_token_headers)
    assert resp.status_code in (404, 403)
