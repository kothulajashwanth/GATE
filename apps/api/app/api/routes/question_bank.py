from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.errors import NotFoundError
from app.db.models.question import QuestionBankFolder, Subject
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.pagination import PaginatedResponse
from app.services.audit import AuditService

router = APIRouter()


class SubjectOut(BaseModel):
    id: str
    name: str
    code: str
    description: str | None = None
    departmentId: str | None = None


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    code: str = Field(min_length=1, max_length=20)
    description: str | None = None
    departmentId: str | None = None


class FolderOut(BaseModel):
    id: str
    name: str
    parentId: str | None = None


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    parentId: str | None = None


@router.get("/subjects", response_model=list[SubjectOut], summary="List subjects")
async def list_subjects(db: Annotated[AsyncSession, Depends(get_db)]) -> list[SubjectOut]:
    result = await db.execute(select(Subject).where(Subject.deleted_at.is_(None)).order_by(Subject.name).limit(200))
    return [SubjectOut(s) for s in result.scalars().all()]


@router.post("/subjects", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
async def create_subject(
    body: SubjectCreate,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SubjectOut:
    existing = await db.execute(select(Subject).where(Subject.code == body.code))
    if existing.scalar_one_or_none():
        raise ValidationError("Subject code already exists")
    subject = Subject(name=body.name, code=body.code, description=body.description, department_id=body.departmentId)
    db.add(subject)
    await db.flush()
    await AuditService.log(db, actor=actor, request=request, action="subject.create", entity_type="subject", entity_id=str(subject.id), new_value=body.model_dump(mode="json"))
    await db.commit()
    return SubjectOut(subject)


@router.get("/folders", response_model=list[FolderOut], summary="List question bank folders")
async def list_folders(db: Annotated[AsyncSession, Depends(get_db)]) -> list[FolderOut]:
    result = await db.execute(select(QuestionBankFolder).where(QuestionBankFolder.deleted_at.is_(None)).order_by(QuestionBankFolder.name).limit(200))
    return [FolderOut(f) for f in result.scalars().all()]


@router.post("/folders", response_model=FolderOut, status_code=status.HTTP_201_CREATED)
async def create_folder(
    body: FolderCreate,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FolderOut:
    folder = QuestionBankFolder(name=body.name, parent_id=body.parentId, created_by=actor.id)
    db.add(folder)
    await db.flush()
    await AuditService.log(db, actor=actor, request=request, action="folder.create", entity_type="folder", entity_id=str(folder.id), new_value=body.model_dump(mode="json"))
    await db.commit()
    return FolderOut(folder)