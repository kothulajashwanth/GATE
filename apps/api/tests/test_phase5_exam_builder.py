import pytest
from datetime import UTC, datetime, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.exam import Exam, ExamQuestion, ExamSchedule, ExamStatus
from app.db.models.question import Question, QuestionType
from app.db.models.user import Role, User


@pytest.mark.asyncio
async def test_exam_builder_crud_and_status_transitions(
    client: AsyncClient, admin_token_headers: dict[str, str], db: AsyncSession, admin_user: User
):
    """Test Exam Creation, Patching, Status Transitions, and Validation."""
    start = datetime.now(UTC) + timedelta(days=1)
    end = start + timedelta(hours=3)

    # 1. Create Exam Draft
    payload = {
        "title": "Data Structures Final Exam",
        "description": "Comprehensive semester exam",
        "durationMinutes": 120,
        "startAt": start.isoformat(),
        "endAt": end.isoformat(),
        "passingMarks": 40,
        "negativeMarksEnabled": True,
        "negativeMarksValue": 0.5,
        "randomizeQuestions": True,
        "shuffleOptions": True,
        "attemptLimit": 1,
        "questionMode": "all_at_once",
        "instructions": "No external aids allowed.",
        "visibility": "private",
        "securityMode": True,
        "cameraProctoringEnabled": False,
        "autoSubmit": True,
    }

    create_res = await client.post("/api/v1/exams", json=payload, headers=admin_token_headers)
    assert create_res.status_code == 201, create_res.text
    exam_data = create_res.json()
    exam_id = exam_data["id"]
    assert exam_data["title"] == "Data Structures Final Exam"
    assert exam_data["status"] == "draft"

    # 2. Update Exam Title & Duration
    update_res = await client.patch(
        f"/api/v1/exams/{exam_id}",
        json={"title": "Data Structures Advanced Final Exam", "durationMinutes": 90},
        headers=admin_token_headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["title"] == "Data Structures Advanced Final Exam"
    assert update_res.json()["durationMinutes"] == 90

    # 3. Test Invalid Status Transition Rejection (DRAFT -> LIVE is invalid)
    bad_trans = await client.post(
        f"/api/v1/exams/{exam_id}/transition",
        json={"target_status": "live"},
        headers=admin_token_headers,
    )
    assert bad_trans.status_code == 400

    # 4. Valid Status Transition (DRAFT -> SCHEDULED)
    good_trans = await client.post(
        f"/api/v1/exams/{exam_id}/transition",
        json={"target_status": "scheduled"},
        headers=admin_token_headers,
    )
    assert good_trans.status_code == 200
    assert good_trans.json()["status"] == "scheduled"


@pytest.mark.asyncio
async def test_exam_question_assignment_and_publishing(
    client: AsyncClient, admin_token_headers: dict[str, str], db: AsyncSession, admin_user: User
):
    """Test assigning approved questions, mark overrides, readiness validation, and publishing."""
    start = datetime.now(UTC) + timedelta(days=2)
    end = start + timedelta(hours=4)

    # 1. Create Question in DB
    q1 = Question(
        type=QuestionType.MCQ,
        text="What is the time complexity of Binary Search?",
        options=["O(N)", "O(log N)", "O(N^2)", "O(1)"],
        correct_answers=["B"],
        marks=2,
        difficulty="medium",
        is_verified=True,
        created_by=admin_user.id,
    )
    q2 = Question(
        type=QuestionType.MCQ,
        text="Which data structure uses LIFO principle?",
        options=["Queue", "Stack", "Tree", "Graph"],
        correct_answers=["B"],
        marks=3,
        difficulty="easy",
        is_verified=True,
        created_by=admin_user.id,
    )
    db.add_all([q1, q2])
    await db.commit()

    # 2. Create Exam
    exam = Exam(
        title="Algorithms Quiz",
        duration_minutes=30,
        start_at=start,
        end_at=end,
        passing_marks=2,
        created_by=admin_user.id,
    )
    db.add(exam)
    await db.commit()
    exam_id = str(exam.id)

    # 3. Assign Questions
    q_assign_res = await client.post(
        f"/api/v1/exams/{exam_id}/questions",
        json={"question_ids": [str(q1.id), str(q2.id)], "marks_override": {str(q1.id): 2, str(q2.id): 3}},
        headers=admin_token_headers,
    )
    assert q_assign_res.status_code == 200, q_assign_res.text
    assert q_assign_res.json()["total_marks"] == 5

    # 4. Check Publish Readiness
    val_res = await client.post(f"/api/v1/exams/{exam_id}/validate", headers=admin_token_headers)
    assert val_res.status_code == 200
    assert val_res.json()["is_ready"] is True

    # 5. Publish Exam
    pub_res = await client.post(f"/api/v1/exams/{exam_id}/publish", headers=admin_token_headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "published"


@pytest.mark.asyncio
async def test_exam_cancellation_and_rbac(
    client: AsyncClient, admin_token_headers: dict[str, str], student_token_headers: dict[str, str], db: AsyncSession, admin_user: User
):
    """Test exam cancellation and verify Student RBAC rejection (HTTP 403)."""
    start = datetime.now(UTC) + timedelta(days=1)
    end = start + timedelta(hours=2)

    exam = Exam(
        title="Physics Midterm",
        duration_minutes=60,
        start_at=start,
        end_at=end,
        created_by=admin_user.id,
    )
    db.add(exam)
    await db.commit()
    exam_id = str(exam.id)

    # Cancel Exam as Admin
    cancel_res = await client.post(
        f"/api/v1/exams/{exam_id}/cancel",
        json={"reason": "Rescheduled due to holiday"},
        headers=admin_token_headers,
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # Verify Student RBAC Rejection (HTTP 403)
    student_res = await client.post(
        f"/api/v1/exams/{exam_id}/cancel",
        json={"reason": "Unauthorized student cancellation attempt"},
        headers=student_token_headers,
    )
    assert student_res.status_code == 403
