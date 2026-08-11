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
async def test_anti_cheat_warning_accumulation_and_termination(
    client: AsyncClient,
    student_token_headers: dict[str, str],
    admin_token_headers: dict[str, str],
    db: AsyncSession,
    student_user: User,
    admin_user: User,
):
    """Test 3-warning accumulation leading to automatic server termination and attempt locking."""
    # 1. Setup Student & Exam
    student = (await db.execute(select(Student).where(Student.user_id == student_user.id))).scalar_one_or_none()
    if not student:
        student = Student(user_id=student_user.id, roll_number="CS2026002", is_active=True)
        db.add(student)
        await db.commit()

    now = datetime.now(UTC)
    exam = Exam(
        title="Operating Systems Security Exam",
        duration_minutes=45,
        start_at=now - timedelta(minutes=5),
        end_at=now + timedelta(hours=1),
        status=ExamStatus.PUBLISHED,
        created_by=admin_user.id,
    )
    db.add(exam)
    await db.commit()

    # 2. Start Exam
    start_res = await client.post("/api/v1/exam-session/start", json={"examId": str(exam.id)}, headers=student_token_headers)
    assert start_res.status_code == 200
    session_id = start_res.json()["sessionId"]

    # 3. Violation 1: Tab Switch (Warning 1)
    v1 = await client.post(
        f"/api/v1/exam-session/{session_id}/violation",
        json={"violationType": "TAB_SWITCH", "reason": "Left tab"},
        headers=student_token_headers,
    )
    assert v1.status_code == 200
    assert v1.json()["warningCount"] == 1
    assert v1.json()["terminated"] is False

    # 4. Violation 2: Fullscreen Exit (Warning 2)
    v2 = await client.post(
        f"/api/v1/exam-session/{session_id}/violation",
        json={"violationType": "FULLSCREEN_EXIT", "reason": "Exited fullscreen"},
        headers=student_token_headers,
    )
    assert v2.status_code == 200
    assert v2.json()["warningCount"] == 2
    assert v2.json()["terminated"] is False

    # 5. Violation 3: Copy Attempt (Warning 3 -> AUTOMATIC TERMINATION)
    v3 = await client.post(
        f"/api/v1/exam-session/{session_id}/violation",
        json={"violationType": "COPY_ATTEMPT", "reason": "Attempted copy"},
        headers=student_token_headers,
    )
    assert v3.status_code == 200
    assert v3.json()["warningCount"] == 3
    assert v3.json()["terminated"] is True
    assert v3.json()["status"] == "terminated"


@pytest.mark.asyncio
async def test_admin_live_monitoring_and_force_termination(
    client: AsyncClient,
    admin_token_headers: dict[str, str],
    student_token_headers: dict[str, str],
    db: AsyncSession,
    student_user: User,
    admin_user: User,
):
    """Test Admin Live Monitoring list and Admin Force Termination API with audit logging."""
    student = (await db.execute(select(Student).where(Student.user_id == student_user.id))).scalar_one_or_none()
    if not student:
        student = Student(user_id=student_user.id, roll_number="CS2026003", is_active=True)
        db.add(student)
        await db.commit()

    now = datetime.now(UTC)
    exam = Exam(
        title="Network Security Quiz",
        duration_minutes=30,
        start_at=now - timedelta(minutes=2),
        end_at=now + timedelta(hours=1),
        status=ExamStatus.PUBLISHED,
        created_by=admin_user.id,
    )
    db.add(exam)
    await db.commit()

    # Student starts session
    start_res = await client.post("/api/v1/exam-session/start", json={"examId": str(exam.id)}, headers=student_token_headers)
    session_id = start_res.json()["sessionId"]

    # 1. Admin views Live Sessions list
    live_res = await client.get("/api/v1/sessions?session_status=active", headers=admin_token_headers)
    assert live_res.status_code == 200
    assert any(s["id"] == session_id for s in live_res.json()["items"])

    # 2. Student attempts to access Admin Live Sessions list (MUST BE REJECTED HTTP 403)
    stud_live = await client.get("/api/v1/sessions", headers=student_token_headers)
    assert stud_live.status_code == 403

    # 3. Admin Force-Terminates Session
    term_res = await client.post(
        f"/api/v1/sessions/{session_id}/admin-terminate",
        json={"reason": "Suspicious remote control activity detected"},
        headers=admin_token_headers,
    )
    assert term_res.status_code == 200
    assert term_res.json()["status"] == "terminated"

    # 4. Verify Student is locked out
    sess_check = await client.get(f"/api/v1/exam-session/{session_id}", headers=student_token_headers)
    assert sess_check.json()["status"] == "terminated"
