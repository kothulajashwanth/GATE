from datetime import datetime, timezone
from io import BytesIO
import os
import pytest
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from sqlalchemy.pool import NullPool

# Override DATABASE_URL for Render PostgreSQL testing
RENDER_DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/gate_db")
os.environ["DATABASE_URL"] = RENDER_DB_URL

import app.core.config as config_module
config_module.get_settings.cache_clear()

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.db.models.audit import AuditLog
from app.db.models.question import FailedQuestion, Question, QuestionOption, QuestionVersion, UploadedFile
from app.db.models.user import Role, User
from app.db.session import get_db
from app.main import app


@pytest.fixture
async def render_db_session():
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url, poolclass=NullPool)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def admin_headers():
    settings = get_settings()
    return {"X-Internal-Key": settings.api_internal_key}


@pytest.fixture
async def student_user_instance(render_db_session: AsyncSession):
    ts = int(datetime.now(timezone.utc).timestamp())
    student_user = User(
        clerk_id=f"clerk_student_{ts}",
        email=f"student_repo_{ts}@example.com",
        first_name="RegularStudent",
        role=Role.STUDENT,
        is_active=True,
    )
    render_db_session.add(student_user)
    await render_db_session.commit()
    return student_user


@pytest.fixture
async def api_client():
    settings = get_settings()
    engine = create_async_engine(settings.async_database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_student_role_authorization_403(api_client: AsyncClient, student_user_instance: User):
    """Verify that regular Student role gets HTTP 403 Forbidden on Admin question endpoints."""
    async def override_student_user():
        return student_user_instance

    app.dependency_overrides[get_current_user] = override_student_user
    try:
        res_list = await api_client.get("/api/v1/questions")
        assert res_list.status_code == 403

        res_upload = await api_client.post("/api/v1/question-bank/files")
        assert res_upload.status_code == 403
    finally:
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]


@pytest.mark.asyncio
async def test_question_repository_file_upload_process_confirm(
    api_client: AsyncClient,
    admin_headers: dict,
    render_db_session: AsyncSession,
):
    """Test full document pipeline: Upload file -> Process & Extract -> Preview -> Confirm -> Save to PostgreSQL."""
    ts = int(datetime.now(timezone.utc).timestamp())

    sample_doc_content = f"""
1. What is the primary function of PostgreSQL in ExamShield AI?
A) Relational database management
B) Frontend styling framework
C) Audio player
D) Web server
Answer: A
Marks: 2
Difficulty: EASY
Explanation: PostgreSQL serves as the persistent relational database foundation.

2. Which programming framework powers the ExamShield backend?
A) Django
B) FastAPI
C) Flask
D) Laravel
Answer: B
Marks: 1
Difficulty: MEDIUM

Invalid Row Without Question Text
""".encode("utf-8")

    # 1. Upload Question Document File
    res_up = await api_client.post(
        "/api/v1/question-bank/files",
        files={"file": (f"test_questions_{ts}.txt", sample_doc_content, "text/plain")},
        headers=admin_headers,
    )
    assert res_up.status_code == 201
    file_data = res_up.json()
    file_id = file_data["id"]
    assert file_data["fileType"] == "txt"

    # 2. Process & Extract Questions
    res_proc = await api_client.post(
        f"/api/v1/question-bank/files/{file_id}/process",
        headers=admin_headers,
    )
    assert res_proc.status_code == 200
    proc_data = res_proc.json()
    assert proc_data["total"] >= 2
    assert len(proc_data["questions"]) >= 2
    assert len(proc_data["failed_questions"]) >= 1

    extracted_q1 = proc_data["questions"][0]
    assert "PostgreSQL" in extracted_q1["text"]
    assert len(extracted_q1["options"]) == 4

    # 3. Confirm Import to PostgreSQL
    res_conf = await api_client.post(
        f"/api/v1/question-bank/import/{file_id}/confirm",
        json={"questions": proc_data["questions"]},
        headers=admin_headers,
    )
    assert res_conf.status_code == 200
    conf_data = res_conf.json()
    assert conf_data["status"] == "COMPLETED"
    assert conf_data["imported_count"] >= 2

    # 4. Verify Question and Version saved in PostgreSQL
    q_res = await render_db_session.execute(
        select(Question).where(Question.source_file_id == file_id).options(selectinload(Question.options_rel), selectinload(Question.versions))
    )
    db_questions = q_res.scalars().all()
    assert len(db_questions) >= 2
    assert db_questions[0].version == 1
    assert len(db_questions[0].options_rel) == 4
    assert len(db_questions[0].versions) == 1


@pytest.mark.asyncio
async def test_question_bank_crud_and_versioning(
    api_client: AsyncClient,
    admin_headers: dict,
    render_db_session: AsyncSession,
):
    """Test Question Bank CRUD, search, filtering, update with version history."""
    ts = int(datetime.now(timezone.utc).timestamp())

    # 1. Create Question
    payload = {
        "type": "mcq",
        "text": f"What is the capital of France? ({ts})",
        "options": ["London", "Paris", "Rome", "Berlin"],
        "correctAnswers": ["B"],
        "explanation": "Paris is the capital of France.",
        "difficulty": "medium",
        "marks": 2,
        "isVerified": True,
    }
    res_create = await api_client.post("/api/v1/questions", json=payload, headers=admin_headers)
    assert res_create.status_code == 201
    q_data = res_create.json()
    question_id = q_data["id"]
    assert q_data["version"] == 1

    # 2. Search & List Questions
    res_list = await api_client.get(
        f"/api/v1/questions?search=France&difficulty=medium",
        headers=admin_headers,
    )
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == question_id for item in list_data["items"])

    # 3. Update Question (Triggers QuestionVersion creation)
    update_payload = {
        "text": f"What is the official capital city of France? ({ts})",
        "marks": 3,
        "changeSummary": "Updated wording and increased marks",
    }
    res_update = await api_client.put(f"/api/v1/questions/{question_id}", json=update_payload, headers=admin_headers)
    assert res_update.status_code == 200
    updated_data = res_update.json()
    assert updated_data["version"] == 2
    assert len(updated_data["versions"]) >= 1

    # 4. Delete Question (Soft delete)
    res_delete = await api_client.delete(f"/api/v1/questions/{question_id}", headers=admin_headers)
    assert res_delete.status_code == 204

    # Verify soft deletion in DB
    db_res = await render_db_session.execute(select(Question).where(Question.id == question_id))
    deleted_q = db_res.scalar_one()
    assert deleted_q.deleted_at is not None
