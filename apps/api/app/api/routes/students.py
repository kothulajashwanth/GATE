from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import PageParams, PaginateParams
from app.core.auth import require_roles
from app.core.errors import NotFoundError
from app.db.models.student import Student
from app.db.models.user import Role, User
from app.db.session import get_db
from app.repositories.student import StudentRepository
from app.repositories.user import UserRepository
from app.schemas.pagination import PaginatedResponse
from app.schemas.student import StudentCreate, StudentRow, StudentUpdate
from app.services.audit import AuditService
from app.services.imports import (
    generate_student_template,
    import_students_from_excel,
    validate_student_import,
)
from app.services.students import StudentService

router = APIRouter()


def _row(student: Student) -> StudentRow:
    dept = student.department
    sem = student.semester
    sec = student.section
    return StudentRow(
        id=str(student.id),
        rollNumber=student.roll_number,
        name=student.user.full_name if student.user else student.roll_number,
        email=student.user.email if student.user else "",
        phone=student.phone,
        isActive=student.user.is_active if student.user else False,
        department={"id": str(dept.id), "name": dept.name} if dept else None,
        semester={"id": str(sem.id), "name": sem.name} if sem else None,
        section={"id": str(sec.id), "name": sec.name} if sec else None,
    )


import logging

logger = logging.getLogger("app")


@router.get("", response_model=PaginatedResponse[StudentRow], summary="List/search students")
async def list_students(
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: PageParams = 1,
    page_size: PaginateParams = 20,
    query: str | None = None,
    department_id: str | None = None,
    semester_id: str | None = None,
    section_id: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[StudentRow]:
    try:
        actor_id_str = str(actor.id) if actor and hasattr(actor, "id") else "unknown"
        logger.info(
            f"[STUDENTS] GET /students request received: actor_id={actor_id_str}, page={page}, page_size={page_size}, query={query}"
        )
        rows, total = await StudentService(db).list(
            query=query,
            department_id=department_id,
            semester_id=semester_id,
            section_id=section_id,
            is_active=is_active,
            page=page,
            page_size=page_size,
        )
        logger.info(f"[STUDENTS] Query completed: total_records={total}, returned_rows={len(rows)}")
        items = [StudentRow(**row) for row in rows]
        return PaginatedResponse.build(items, page, page_size, total)
    except Exception as exc:
        logger.error(
            f"[STUDENTS_ERROR] GET /students failed: {exc.__class__.__name__}: {str(exc)}",
            exc_info=True,
        )
        raise


@router.get("/template", summary="Download student bulk import template (.xlsx)")
async def download_template(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
) -> StreamingResponse:
    buf = generate_student_template()
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="student_import_template.xlsx"'},
    )


@router.get("/export", summary="Export students as Excel roster")
async def export_students(
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    query: str | None = None,
    department_id: str | None = None,
    semester_id: str | None = None,
    section_id: str | None = None,
    is_active: bool | None = None,
) -> StreamingResponse:
    from openpyxl import Workbook

    rows, _ = await StudentService(db).list(
        query=query,
        department_id=department_id,
        semester_id=semester_id,
        section_id=section_id,
        is_active=is_active,
        page=1,
        page_size=100000,
    )
    wb = Workbook()
    ws = wb.active
    ws.title = "Student Roster"
    ws.append(["Roll Number", "Name", "Email", "Phone", "Department", "Semester", "Section", "Status"])
    for r in rows:
        ws.append([
            r["rollNumber"],
            r["name"],
            r["email"],
            r.get("phone") or "",
            r["department"]["name"] if r.get("department") else "",
            r["semester"]["name"] if r.get("semester") else "",
            r["section"]["name"] if r.get("section") else "",
            "Active" if r.get("isActive") else "Inactive",
        ])

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="STUDENT_EXPORT_REQUESTED",
        entity_type="student",
        new_value={"total_exported": len(rows)},
    )
    await db.commit()

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="student_roster.xlsx"'},
    )


@router.post("/import/validate", response_model=dict, summary="Validate student import file before confirmation")
async def validate_import(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
) -> dict:
    content = await file.read()
    return await validate_student_import(db, BytesIO(content))


@router.post("/import", response_model=dict, summary="Import validated student roster into PostgreSQL")
async def import_students(
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
) -> dict:
    content = await file.read()
    result = await import_students_from_excel(db, BytesIO(content))
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="STUDENT_IMPORTED",
        entity_type="student",
        new_value={"total": result.total, "imported": result.imported, "failed": result.failed},
    )
    await db.commit()
    return {
        "total": result.total,
        "imported": result.imported,
        "failed": result.failed,
        "errors": result.errors[:100],
    }


@router.get("/{student_id}", response_model=StudentRow, summary="Student detail")
async def get_student(
    student_id: str,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StudentRow:
    result = await db.execute(
        select(Student)
        .where(Student.id == student_id, Student.deleted_at.is_(None))
        .options(
            selectinload(Student.user),
            selectinload(Student.department),
            selectinload(Student.semester),
            selectinload(Student.section),
        )
    )
    student = result.scalar_one_or_none()
    if student is None:
        raise NotFoundError("Student not found")
    return _row(student)


@router.post("", response_model=StudentRow, status_code=status.HTTP_201_CREATED, summary="Create student")
async def create_student(
    body: StudentCreate,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StudentRow:
    user = await UserRepository(db).create_user(
        email=body.email,
        first_name=body.firstName,
        last_name=body.lastName,
        phone=body.phone,
        role=Role.STUDENT,
        is_active=True,
    )
    student = await StudentRepository(db).create_student(
        user=user,
        roll_number=body.rollNumber,
        department_id=body.departmentId,
        semester_id=body.semesterId,
        section_id=body.sectionId,
        phone=body.phone,
        parent_name=body.parentName,
        parent_phone=body.parentPhone,
        enrollment_year=body.enrollmentYear,
    )
    await db.flush()
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="STUDENT_CREATED",
        entity_type="student",
        entity_id=str(student.id),
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(student)

    # Fetch loaded relationships
    res = await db.execute(
        select(Student)
        .where(Student.id == student.id)
        .options(
            selectinload(Student.user),
            selectinload(Student.department),
            selectinload(Student.semester),
            selectinload(Student.section),
        )
    )
    return _row(res.scalar_one())


@router.put("/{student_id}", response_model=StudentRow, summary="Update student")
@router.patch("/{student_id}", response_model=StudentRow, summary="Update student")
async def update_student(
    student_id: str,
    body: StudentUpdate,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StudentRow:
    repo = StudentRepository(db)
    student = await repo.get(student_id)
    old_value = {
        "rollNumber": student.roll_number,
        "isActive": student.user.is_active if student.user else None,
    }

    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    if "firstName" in updates or "lastName" in updates:
        if student.user:
            if "firstName" in updates:
                student.user.first_name = updates["firstName"]
            if "lastName" in updates:
                student.user.last_name = updates["lastName"]

    if any(k in updates for k in ("departmentId", "semesterId", "sectionId")):
        if "departmentId" in updates:
            student.department_id = updates["departmentId"]
        if "semesterId" in updates:
            student.semester_id = updates["semesterId"]
        if "sectionId" in updates:
            student.section_id = updates["sectionId"]

    if "phone" in updates:
        student.phone = updates["phone"]
        if student.user:
            student.user.phone = updates["phone"]

    if "isActive" in updates and student.user:
        student.user.is_active = updates["isActive"]

    await db.flush()
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="STUDENT_UPDATED",
        entity_type="student",
        entity_id=str(student.id),
        old_value=old_value,
        new_value=body.model_dump(mode="json", exclude_none=True),
    )
    await db.commit()

    res = await db.execute(
        select(Student)
        .where(Student.id == student.id)
        .options(
            selectinload(Student.user),
            selectinload(Student.department),
            selectinload(Student.semester),
            selectinload(Student.section),
        )
    )
    return _row(res.scalar_one())


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Deactivate / soft delete student")
async def delete_student(
    student_id: str,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    repo = StudentRepository(db)
    student = await repo.get(student_id)
    if student.user:
        student.user.is_active = False
    await repo.soft_delete(student_id)
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="STUDENT_DEACTIVATED",
        entity_type="student",
        entity_id=student_id,
        old_value={"rollNumber": student.roll_number},
    )
    await db.commit()
