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
from app.db.models.academic import Department, Section, Semester
from app.db.models.audit import AuditLog
from app.db.models.student import Student
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
        email=f"student_auth_{ts}@example.com",
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
    """Verify that regular Student role gets HTTP 403 Forbidden on Admin endpoints."""
    async def override_student_user():
        return student_user_instance

    app.dependency_overrides[get_current_user] = override_student_user
    try:
        res_list = await api_client.get("/api/v1/students")
        assert res_list.status_code == 403

        res_create = await api_client.post(
            "/api/v1/students",
            json={"rollNumber": "TEST403", "email": "test403@example.com", "firstName": "Test"},
        )
        assert res_create.status_code == 403
    finally:
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]


@pytest.mark.asyncio
async def test_student_crud_lifecycle(
    api_client: AsyncClient,
    admin_headers: dict,
    render_db_session: AsyncSession,
):
    """Test complete Student CRUD: create, duplicate checks, search, update, deactivate."""
    ts = int(datetime.now(timezone.utc).timestamp())

    # Create Placement reference rows
    dept = Department(name=f"ECE Dept {ts}", code=f"ECE_{ts}")
    render_db_session.add(dept)
    await render_db_session.flush()

    sem = Semester(department_id=dept.id, name=f"Semester 3 {ts}", ordinal=3)
    render_db_session.add(sem)
    await render_db_session.flush()

    sec = Section(department_id=dept.id, semester_id=sem.id, name="Sec 1", code=f"SEC1_{ts}")
    render_db_session.add(sec)
    await render_db_session.commit()

    # 1. Create Student
    payload = {
        "rollNumber": f"ECE_{ts}_001",
        "email": f"ece_student_{ts}@college.edu",
        "firstName": "Robert",
        "lastName": "Paulson",
        "phone": "9876543210",
        "departmentId": str(dept.id),
        "semesterId": str(sem.id),
        "sectionId": str(sec.id),
    }
    res_create = await api_client.post("/api/v1/students", json=payload, headers=admin_headers)
    assert res_create.status_code == 201
    created_data = res_create.json()
    assert created_data["rollNumber"] == f"ECE_{ts}_001"
    student_id = created_data["id"]

    # 2. Duplicate Email Check (409 Conflict)
    dup_email_payload = {**payload, "rollNumber": f"ECE_{ts}_002"}
    res_dup_email = await api_client.post("/api/v1/students", json=dup_email_payload, headers=admin_headers)
    assert res_dup_email.status_code in {409, 422}

    # 3. Duplicate Roll Number Check (409 Conflict)
    dup_roll_payload = {**payload, "email": f"different_{ts}@college.edu"}
    res_dup_roll = await api_client.post("/api/v1/students", json=dup_roll_payload, headers=admin_headers)
    assert res_dup_roll.status_code in {409, 422}

    # 4. Search & List Students
    res_list = await api_client.get(
        f"/api/v1/students?query=Robert&department_id={dept.id}",
        headers=admin_headers,
    )
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert list_data["total"] >= 1
    assert any(item["id"] == student_id for item in list_data["items"])

    # 5. Update Student (PUT / PATCH)
    update_payload = {"firstName": "Bobby", "phone": "1112223333", "isActive": True}
    res_update = await api_client.put(f"/api/v1/students/{student_id}", json=update_payload, headers=admin_headers)
    assert res_update.status_code == 200
    updated_data = res_update.json()
    assert updated_data["name"] == "Bobby Paulson"

    # 6. Deactivate / Soft Delete Student
    res_delete = await api_client.delete(f"/api/v1/students/{student_id}", headers=admin_headers)
    assert res_delete.status_code == 204

    # Verify soft deletion in DB
    db_res = await render_db_session.execute(
        select(Student).where(Student.id == student_id).options(selectinload(Student.user))
    )
    deleted_student = db_res.scalar_one()
    assert deleted_student.deleted_at is not None
    assert deleted_student.user.is_active is False


@pytest.mark.asyncio
async def test_excel_template_import_export_workflow(
    api_client: AsyncClient,
    admin_headers: dict,
    render_db_session: AsyncSession,
):
    """Test Excel Template download, Excel Import validate & confirm, and Excel Export roster."""
    ts = int(datetime.now(timezone.utc).timestamp())

    # Create placement department for import test
    dept = Department(name=f"Mechanical {ts}", code=f"MECH_{ts}")
    render_db_session.add(dept)
    await render_db_session.flush()

    sem = Semester(department_id=dept.id, name=f"Semester 1 {ts}", ordinal=1)
    render_db_session.add(sem)
    await render_db_session.flush()

    sec = Section(department_id=dept.id, semester_id=sem.id, name="Section A", code=f"SEC_MECH_{ts}")
    render_db_session.add(sec)
    await render_db_session.commit()

    # 1. Download Excel Template
    res_temp = await api_client.get("/api/v1/students/template", headers=admin_headers)
    assert res_temp.status_code == 200
    assert "spreadsheetml" in res_temp.headers.get("content-type", "")

    # 2. Build test Excel workbook for import
    wb = Workbook()
    ws = wb.active
    ws.append(["full_name", "email", "roll_number", "phone", "department", "semester", "section", "status"])
    ws.append(["Imported Student", f"imported_{ts}@mech.edu", f"MECH_{ts}_101", "9988776655", f"MECH_{ts}", "1", f"SEC_MECH_{ts}", "ACTIVE"])

    buf = BytesIO()
    wb.save(buf)
    file_bytes = buf.getvalue()

    # 3. Validate Import Preview
    res_val = await api_client.post(
        "/api/v1/students/import/validate",
        files={"file": ("test_roster.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=admin_headers,
    )
    assert res_val.status_code == 200
    val_data = res_val.json()
    assert val_data["valid_count"] == 1
    assert val_data["invalid_count"] == 0

    # 4. Confirm Import
    res_imp = await api_client.post(
        "/api/v1/students/import",
        files={"file": ("test_roster.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=admin_headers,
    )
    assert res_imp.status_code == 200
    imp_data = res_imp.json()
    assert imp_data["imported"] == 1

    # 5. Export Roster
    res_exp = await api_client.get("/api/v1/students/export", headers=admin_headers)
    assert res_exp.status_code == 200
    assert "spreadsheetml" in res_exp.headers.get("content-type", "")

    # 6. Verify Audit Logs recorded
    audit_res = await render_db_session.execute(
        select(AuditLog).where(AuditLog.action.in_(["STUDENT_CREATED", "STUDENT_IMPORTED", "STUDENT_EXPORT_REQUESTED", "STUDENT_DEACTIVATED"]))
    )
    logs = audit_res.scalars().all()
    assert len(logs) >= 1
