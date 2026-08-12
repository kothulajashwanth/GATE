import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.exam import Exam, ExamQuestion
from app.db.models.question import BloomLevel, Difficulty, Question, QuestionVersion
from app.db.models.user import Role, User
from app.services.ai import AIQuestion, GeminiProvider, MockProvider, OpenAIProvider, get_ai_provider


@pytest.mark.asyncio
async def test_ai_provider_abstraction():
    """Test AI provider factory and MockProvider generation."""
    provider = get_ai_provider()
    assert isinstance(provider, (MockProvider, GeminiProvider, OpenAIProvider))

    mock = MockProvider()
    questions = await mock.generate_questions(
        prompt="Test operating system concepts",
        count=3,
        difficulty="medium",
        question_type="mcq",
        topic="OS",
        bloom_level="apply",
    )

    assert len(questions) == 3
    for q in questions:
        assert isinstance(q, AIQuestion)
        assert q.type == "mcq"
        assert q.difficulty == "medium"
        assert q.bloom_level == "apply"
        assert len(q.options) == 4
        assert q.correct_answers == ["A"]


@pytest.mark.asyncio
async def test_ai_generate_questions_endpoint(client: AsyncClient, admin_token_headers: dict[str, str]):
    """Test POST /api/v1/ai/generate-questions endpoint with Admin role."""
    payload = {
        "prompt": "Generate 4 Operating System questions",
        "count": 4,
        "difficulty": "medium",
        "question_type": "mcq",
        "topic": "Process Scheduling",
        "bloom_level": "understand",
    }
    resp = await client.post("/api/v1/ai/generate-questions", json=payload, headers=admin_token_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 4
    assert data[0]["difficulty"] == "medium"
    assert data[0]["bloom_level"] == "understand"
    assert "text" in data[0]


@pytest.mark.asyncio
async def test_ai_approve_questions_workflow(client: AsyncClient, admin_token_headers: dict[str, str], db: AsyncSession):
    """Test human approval workflow: saving AI questions into PostgreSQL Question Bank."""
    payload = {
        "questions": [
            {
                "type": "mcq",
                "text": "What is the primary function of an Operating System Kernel?",
                "options": ["Manage System Resources", "Web Browsing", "Compile Code", "Design Graphics"],
                "correctAnswers": ["A"],
                "explanation": "The kernel manages hardware resources and system execution.",
                "difficulty": "easy",
                "bloomLevel": "remember",
                "marks": 1,
                "topic": "Operating Systems",
            }
        ]
    }
    resp = await client.post("/api/v1/ai/questions/approve", json=payload, headers=admin_token_headers)
    assert resp.status_code == 200, resp.text
    res_data = resp.json()
    assert res_data["approved_count"] == 1
    q_id = res_data["question_ids"][0]

    # Verify PostgreSQL insertion
    q = (await db.execute(select(Question).where(Question.id == q_id))).scalar_one()
    assert q.text == "What is the primary function of an Operating System Kernel?"
    assert q.is_ai_generated is True
    assert q.is_verified is True
    assert q.bloom_level == BloomLevel.REMEMBER
    assert q.difficulty == Difficulty.EASY

    # Verify version history snapshot
    ver = (await db.execute(select(QuestionVersion).where(QuestionVersion.question_id == q_id))).scalar_one()
    assert ver.version == 1
    assert ver.change_summary == "Approved AI generated question"


@pytest.mark.asyncio
async def test_blueprint_check_availability_and_gap_filling(
    client: AsyncClient, admin_token_headers: dict[str, str], db: AsyncSession, admin_user: User
):
    """Test Exam Blueprint availability check, AI gap filling, and exam assembly."""
    # 1. Create an Exam schedule target
    exam = Exam(
        title="Midterm OS Exam",
        duration_minutes=60,
        total_marks=50,
        passing_marks=20,
        created_by=admin_user.id,
    )
    db.add(exam)
    await db.commit()
    await db.refresh(exam)

    # 2. Check Blueprint availability
    rules_payload = {
        "exam_id": str(exam.id),
        "rules": [
            {"topic": "OS Kernel", "difficulty": "easy", "bloom_level": "remember", "count": 2, "marks": 1},
            {"topic": "OS Kernel", "difficulty": "hard", "bloom_level": "analyze", "count": 3, "marks": 4},
        ],
    }
    avail_resp = await client.post("/api/v1/ai/blueprints/check-availability", json=rules_payload, headers=admin_token_headers)
    assert avail_resp.status_code == 200, avail_resp.text
    avail_data = avail_resp.json()
    assert avail_data["total_requested"] == 5

    # 3. Fill gaps with AI
    gap_resp = await client.post("/api/v1/ai/blueprints/fill-gaps", json=rules_payload, headers=admin_token_headers)
    assert gap_resp.status_code == 200, gap_resp.text
    gap_data = gap_resp.json()
    assert gap_data["generated_count"] >= 1

    # 4. Assemble questions into Exam
    asm_resp = await client.post("/api/v1/ai/blueprints/assemble-exam", json=rules_payload, headers=admin_token_headers)
    assert asm_resp.status_code == 200, asm_resp.text
    asm_data = asm_resp.json()
    assert asm_data["assembled_count"] >= 1

    # Verify ExamQuestion records in PostgreSQL
    eq_links = (await db.execute(select(ExamQuestion).where(ExamQuestion.exam_id == exam.id))).scalars().all()
    assert len(eq_links) >= 1


@pytest.mark.asyncio
async def test_student_role_authorization_rejection(client: AsyncClient, student_token_headers: dict[str, str]):
    """Test that Student roles receive HTTP 403 Forbidden on all AI and Blueprint endpoints."""
    endpoints = [
        ("/api/v1/ai/generate-questions", "post", {"prompt": "Test", "count": 1}),
        ("/api/v1/ai/questions/approve", "post", {"questions": []}),
        ("/api/v1/ai/blueprints/check-availability", "post", {"rules": []}),
        ("/api/v1/ai/blueprints/fill-gaps", "post", {"rules": []}),
        ("/api/v1/ai/blueprints/assemble-exam", "post", {"rules": []}),
    ]

    for ep, method, body in endpoints:
        resp = await client.post(ep, json=body, headers=student_token_headers)
        assert resp.status_code == 403, f"Expected 403 for {ep}, got {resp.status_code}"
