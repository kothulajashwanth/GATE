from datetime import date, datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.db.models.academic import Department, Section, Semester
from app.db.models.attendance import AttendanceRecord, AttendanceSession, AttendanceStatus, SessionState
from app.db.models.base import Base
from app.db.models.question import Subject
from app.db.models.student import Student
from app.db.models.user import Role, User
from app.db.session import get_db
from app.main import app


@pytest.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def api_client(test_db: AsyncSession):
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_user(test_db: AsyncSession):
    ts = int(datetime.now(timezone.utc).timestamp())
    admin = User(
        clerk_id=f"admin_clerk_{ts}",
        email=f"admin_{ts}@example.com",
        first_name="Admin",
        role=Role.ADMIN,
        is_active=True,
    )
    test_db.add(admin)
    await test_db.commit()
    await test_db.refresh(admin)
    return admin


@pytest.fixture
async def student_user(test_db: AsyncSession):
    ts = int(datetime.now(timezone.utc).timestamp())
    stud = User(
        clerk_id=f"stud_clerk_{ts}",
        email=f"student_{ts}@example.com",
        first_name="StudentOne",
        role=Role.STUDENT,
        is_active=True,
    )
    test_db.add(stud)
    await test_db.commit()
    await test_db.refresh(stud)
    return stud


@pytest.fixture
async def admin_headers():
    return {"X-Internal-Key": get_settings().api_internal_key}


@pytest.mark.asyncio
async def test_attendance_workflow_end_to_end(
    api_client: AsyncClient,
    admin_headers: dict[str, str],
    test_db: AsyncSession,
    admin_user: User,
    student_user: User,
):
    # 1. Override auth to act as admin
    async def override_admin_user():
        return admin_user

    app.dependency_overrides[get_current_user] = override_admin_user

    # 2. Empty sessions check
    res_empty = await api_client.get("/api/v1/attendance/sessions", headers=admin_headers)
    assert res_empty.status_code == 200
    assert res_empty.json() == []

    # 3. Create Department, Semester, Section, Subject
    dept = Department(name="Computer Science", code="CSE", description="CS Dept")
    sem = Semester(name="Semester 6", number=6)
    sec = Section(name="Section A")
    subj = Subject(name="Computer Networks", code="CS601", description="Networks")
    test_db.add_all([dept, sem, sec, subj])
    await test_db.commit()

    student = Student(
        user_id=student_user.id,
        roll_number="CSE2026001",
        department_id=dept.id,
        semester_id=sem.id,
        section_id=sec.id,
    )
    test_db.add(student)
    await test_db.commit()

    # 4. Create Session (POST /api/v1/attendance/sessions)
    create_payload = {
        "title": "CN Morning Attendance",
        "subject_id": str(subj.id),
        "department_id": str(dept.id),
        "semester_id": str(sem.id),
        "section_id": str(sec.id),
        "date": str(date.today()),
        "start_time": "09:00",
        "duration_minutes": 60,
        "status": "ACTIVE",
    }
    res_create = await api_client.post(
        "/api/v1/attendance/sessions", json=create_payload, headers=admin_headers
    )
    assert res_create.status_code == 200, res_create.text
    sess_data = res_create.json()
    assert sess_data["title"] == "CN Morning Attendance"
    assert sess_data["subject_name"] == "Computer Networks"
    assert sess_data["department_name"] == "Computer Science"
    assert sess_data["status"] == "ACTIVE"
    session_id = sess_data["id"]

    # 5. List Sessions (GET /api/v1/attendance/sessions)
    res_list = await api_client.get("/api/v1/attendance/sessions", headers=admin_headers)
    assert res_list.status_code == 200
    list_items = res_list.json()
    assert len(list_items) == 1
    assert list_items[0]["id"] == session_id

    # 6. Session Detail & Roster (GET /api/v1/attendance/sessions/{session_id})
    res_detail = await api_client.get(
        f"/api/v1/attendance/sessions/{session_id}", headers=admin_headers
    )
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["session"]["id"] == session_id
    assert len(detail_data["records"]) == 1
    assert detail_data["records"][0]["roll_number"] == "CSE2026001"
    assert detail_data["records"][0]["status"] == "PENDING"

    # 7. Student check-in (POST /api/v1/attendance/student/submit)
    async def override_student():
        return student_user

    app.dependency_overrides[get_current_user] = override_student

    # Student active session check
    res_active = await api_client.get("/api/v1/attendance/student/active")
    assert res_active.status_code == 200
    active_data = res_active.json()
    assert active_data is not None
    assert active_data["id"] == session_id

    # Submit attendance
    res_submit = await api_client.post(
        "/api/v1/attendance/student/submit",
        json={"session_id": session_id, "status": "PRESENT"},
    )
    assert res_submit.status_code == 200
    submit_data = res_submit.json()
    assert submit_data["status"] == "PRESENT"

    # Verify student records history
    res_hist = await api_client.get("/api/v1/attendance/student/records")
    assert res_hist.status_code == 200
    hist_data = res_hist.json()
    assert hist_data["total_sessions"] == 1
    assert hist_data["present_count"] == 1
    assert hist_data["overall_percentage"] == 100.0

    # 8. Close session as admin
    app.dependency_overrides[get_current_user] = override_admin_user
    res_close = await api_client.post(
        f"/api/v1/attendance/sessions/{session_id}/close", json={}, headers=admin_headers
    )
    assert res_close.status_code == 200
    closed_data = res_close.json()
    assert closed_data["status"] == "CLOSED"

    # 9. CSV Export (GET /api/v1/attendance/sessions/{session_id}/export)
    res_export = await api_client.get(
        f"/api/v1/attendance/sessions/{session_id}/export", headers=admin_headers
    )
    assert res_export.status_code == 200
    assert "text/csv" in res_export.headers.get("content-type", "")
    assert "CSE2026001" in res_export.text
