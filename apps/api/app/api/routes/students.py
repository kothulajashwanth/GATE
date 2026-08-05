from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import PageParams, PaginateParams
from app.core.auth import require_roles
from app.core.errors import NotFoundError
from app.db.models.user import Role, User
from app.db.session import get_db
from app.repositories.student import StudentRepository
from app.repositories.user import UserRepository
from app.schemas.pagination import PaginatedResponse
from app.schemas.student import StudentCreate, StudentRow, StudentUpdate
from app.services.audit import AuditService
from app.services.students import StudentService

router = APIRouter()


def _row(student) -> StudentRow:
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


@router.get("", response_model=PaginatedResponse[StudentRow], summary="List/search students")
async def list_students(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: PageParams = 1,
    page_size: PaginateParams = 20,
    query: str | None = None,
    department_id: str | None = None,
    semester_id: str | None = None,
    section_id: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[StudentRow]:
    rows, total = await StudentService(db).list(
        query=query,
        department_id=department_id,
        semester_id=semester_id,
        section_id=section_id,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )
    items = [StudentRow(**row) for row in rows]
    return PaginatedResponse.build(items, page, page_size, total)


@router.get("/export", summary="Export students as Excel")
async def export_students(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StreamingResponse:
    from openpyxl import Workbook

    rows, _ = await StudentService(db).list(page=1, page_size=100000)
    wb = Workbook()
    ws = wb.active
    ws.title = "Students"
    ws.append(["Roll Number", "Name", "Email", "Phone", "Department", "Semester", "Section", "Status"])
    for r in rows:
        ws.append([
            r["rollNumber"],
            r["name"],
            r["email"],
            r.get("phone") or "",
            r["department"]["name"] if r["department"] else "",
            r["semester"]["name"] if r["semester"] else "",
            r["section"]["name"] if r["section"] else "",
            "Active" if r["isActive"] else "Inactive",
        ])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="students.xlsx"'},
    )


@router.post("/import", response_model=dict, summary="Import students from Excel (with validation)")
async def import_students(
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: Annotated[UploadFile, File(...)],
) -> dict:
    from app.services.imports import import_students_from_excel

    content = await file.read()
    result = await import_students_from_excel(db, BytesIO(content))
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="student.import",
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
    from sqlalchemy.orm import selectinload

    from app.db.models.student import Student

    result = await db.execute(
        select(Student)
        .where(Student.id == student_id, Student.deleted_at.is_(None))
        .options(selectinload(Student.user), selectinload(Student.department), selectinload(Student.semester), selectinload(Student.section))
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
    # create the platform account (no Clerk ID yet; linked on first sign-in via email)
    user = await UserRepository(db).create(
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
        action="student.create",
        entity_type="student",
        entity_id=str(student.id),
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    await db.refresh(student)
    return _row(student)


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
    old_value = {"rollNumber": student.roll_number, "isActive": student.user.is_active if student.user else None}

    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    if any(k in updates for k in ("departmentId", "semesterId", "sectionId")):
        student.department_id = updates.get("departmentId", student.department_id)
        student.semester_id = updates.get("semesterId", student.semester_id)
        student.section_id = updates.get("sectionId", student.section_id)
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
        action="student.update",
        entity_type="student",
        entity_id=str(student.id),
        old_value=old_value,
        new_value=body.model_dump(mode="json", exclude_none=True),
    )
    await db.commit()
    await db.refresh(student)
    return _row(student)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete student (soft)")
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
        action="student.delete",
        entity_type="student",
        entity_id=student_id,
        old_value={"rollNumber": student.roll_number},
    )
    await db.commit()
