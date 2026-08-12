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
async def test_automatic_evaluation_negative_marking_and_pass_fail(
    client: AsyncClient,
    student_token_headers: dict[str, str],
    admin_token_headers: dict[str, str],
    db: AsyncSession,
    student_user: User,
    admin_user: User,
):
    """Test automatic objective evaluation, negative marking deduction, and pass/fail thresholds."""
    # 1. Setup Student
    student = (await db.execute(select(Student).where(Student.user_id == student_user.id))).scalar_one_or_none()
    if not student:
        student = Student(user_id=student_user.id, roll_number="CS2026004", is_active=True)
        db.add(student)
        await db.commit()

    # 2. Setup Questions (q1: 4 marks, q2: 4 marks, negative 1 mark)
    q1 = Question(
        type=QuestionType.MCQ,
        text="What is 2 + 2?",
        options=["3", "4", "5", "6"],
        correct_answers=["B"],
        marks=4,
        negative_marks=1.0,
        is_verified=True,
        created_by=admin_user.id,
    )
    q2 = Question(
        type=QuestionType.MCQ,
        text="Which gas is essential for human respiration?",
        options=["Nitrogen", "Oxygen", "CO2", "Helium"],
        correct_answers=["B"],
        marks=4,
        negative_marks=1.0,
        is_verified=True,
        created_by=admin_user.id,
    )
    db.add_all([q1, q2])
    await db.commit()

    now = datetime.now(UTC)
    exam = Exam(
        title="General Knowledge & Math Test",
        duration_minutes=30,
        start_at=now - timedelta(minutes=5),
        end_at=now + timedelta(hours=1),
        passing_marks=50,  # 50% passing threshold
        negative_marks_enabled=True,
        negative_marks_value=1.0,
        status=ExamStatus.PUBLISHED,
        created_by=admin_user.id,
    )
    db.add(exam)
    await db.commit()

    db.add(ExamQuestion(exam_id=exam.id, question_id=q1.id, order_index=1, marks=4))
    db.add(ExamQuestion(exam_id=exam.id, question_id=q2.id, order_index=2, marks=4))
    await db.commit()

    # 3. Start Session & Answer (q1 correct "B" -> +4, q2 incorrect "A" -> -1. Total = 3 / 8 = 37.5%)
    start_res = await client.post("/api/v1/exam-session/start", json={"examId": str(exam.id)}, headers=student_token_headers)
    session_id = start_res.json()["sessionId"]

    await client.post(f"/api/v1/exam-session/{session_id}/answer", json={"questionId": str(q1.id), "answer": ["B"]}, headers=student_token_headers)
    await client.post(f"/api/v1/exam-session/{session_id}/answer", json={"questionId": str(q2.id), "answer": ["A"]}, headers=student_token_headers)

    # 4. Submit Exam
    sub_res = await client.post(f"/api/v1/exam-session/{session_id}/submit", headers=student_token_headers)
    assert sub_res.status_code == 200

    # 5. Check Evaluated Result in DB
    result = (await db.execute(select(ExamResult).where(ExamResult.session_id == session_id))).scalar_one_or_none()
    assert result is not None
    assert result.obtained_marks == 3.0
    assert result.total_marks == 8.0
    assert result.percentage == 37.5
    assert result.is_passed is False  # 37.5% < 50% passing threshold


@pytest.mark.asyncio
async def test_result_publication_and_student_privacy(
    client: AsyncClient,
    admin_token_headers: dict[str, str],
    student_token_headers: dict[str, str],
    db: AsyncSession,
    student_user: User,
    admin_user: User,
):
    """Test Result publication and verify Student privacy protection."""
    student = (await db.execute(select(Student).where(Student.user_id == student_user.id))).scalar_one_or_none()
    if not student:
        student = Student(user_id=student_user.id, roll_number="CS2026005", is_active=True)
        db.add(student)
        await db.commit()

    now = datetime.now(UTC)
    exam = Exam(
        title="Privacy & Security Quiz",
        duration_minutes=20,
        start_at=now - timedelta(minutes=2),
        end_at=now + timedelta(hours=1),
        status=ExamStatus.PUBLISHED,
        created_by=admin_user.id,
    )
    db.add(exam)
    await db.commit()

    res = ExamResult(
        session_id=student.id,  # dummy session link
        exam_id=exam.id,
        student_id=student.id,
        total_marks=10.0,
        obtained_marks=8.0,
        percentage=80.0,
        is_passed=True,
        status=ResultStatus.AUTO,
    )
    db.add(res)
    await db.commit()
    result_id = str(res.id)

    # 1. Student requests my_results prior to publication (Should return empty or unpublished)
    before_pub = await client.get("/api/v1/results/me", headers=student_token_headers)
    assert before_pub.status_code == 200
    assert not any(r["id"] == result_id for r in before_pub.json()["items"])

    # 2. Admin publishes single result
    pub_res = await client.post(f"/api/v1/results/admin/{result_id}/publish", headers=admin_token_headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "published"

    # 3. Student requests my_results after publication (Should appear now)
    after_pub = await client.get("/api/v1/results/me", headers=student_token_headers)
    assert after_pub.status_code == 200
    assert any(r["id"] == result_id for r in after_pub.json()["items"])
