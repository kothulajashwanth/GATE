from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.db.models.user import Role, User
from app.db.session import get_db
from app.repositories.academic import DepartmentRepository, SectionRepository, SemesterRepository
from app.services.audit import AuditService

router = APIRouter()


class DepartmentOut(BaseModel):
    id: str
    name: str
    code: str
    description: str | None = None


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    code: str = Field(min_length=1, max_length=20)
    description: str | None = None


class SemesterOut(BaseModel):
    id: str
    departmentId: str
    name: str
    ordinal: int


class SectionOut(BaseModel):
    id: str
    departmentId: str
    semesterId: str
    name: str
    code: str


def _dept(d) -> DepartmentOut:
    return DepartmentOut(id=str(d.id), name=d.name, code=d.code, description=d.description)


def _sem(s) -> SemesterOut:
    return SemesterOut(id=str(s.id), departmentId=str(s.department_id), name=s.name, ordinal=s.ordinal)


def _sec(s) -> SectionOut:
    return SectionOut(
        id=str(s.id),
        departmentId=str(s.department_id),
        semesterId=str(s.semester_id),
        name=s.name,
        code=s.code,
    )


@router.get("/departments", response_model=list[DepartmentOut], summary="List departments")
async def list_departments(db: Annotated[AsyncSession, Depends(get_db)]) -> list[DepartmentOut]:
    rows = await DepartmentRepository(db).list(limit=200)
    return [_dept(d) for d in rows]


@router.post("/departments", response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
async def create_department(
    body: DepartmentCreate,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DepartmentOut:
    dept = await DepartmentRepository(db).create_with_check(
        name=body.name, code=body.code, description=body.description
    )
    await AuditService.log(
        db, actor=actor, request=request, action="department.create",
        entity_type="department", entity_id=str(dept.id), new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    return _dept(dept)


@router.get("/semesters", response_model=list[SemesterOut], summary="List all semesters")
async def list_all_semesters(
    db: Annotated[AsyncSession, Depends(get_db)],
    department_id: str | None = None,
) -> list[SemesterOut]:
    if department_id:
        rows = await SemesterRepository(db).list_by_department(department_id)
    else:
        rows = await SemesterRepository(db).list(limit=200)
    return [_sem(s) for s in rows]


@router.get("/sections", response_model=list[SectionOut], summary="List all sections")
async def list_all_sections(
    db: Annotated[AsyncSession, Depends(get_db)],
    department_id: str | None = None,
    semester_id: str | None = None,
) -> list[SectionOut]:
    if semester_id:
        rows = await SectionRepository(db).list_by_semester(semester_id)
    elif department_id:
        rows = await SectionRepository(db).list_by_department(department_id)
    else:
        rows = await SectionRepository(db).list(limit=200)
    return [_sec(s) for s in rows]


@router.get("/departments/{department_id}/semesters", response_model=list[SemesterOut])
async def list_semesters(
    department_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SemesterOut]:
    rows = await SemesterRepository(db).list_by_department(department_id)
    return [_sem(s) for s in rows]


@router.get("/departments/{department_id}/sections", response_model=list[SectionOut])
async def list_sections(
    department_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SectionOut]:
    rows = await SectionRepository(db).list_by_department(department_id)
    return [_sec(s) for s in rows]


@router.get("/semesters/{semester_id}/sections", response_model=list[SectionOut])
async def list_sections_by_semester(
    semester_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SectionOut]:
    rows = await SectionRepository(db).list_by_semester(semester_id)
    return [_sec(s) for s in rows]

