from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.errors import NotFoundError
from app.db.models.question import (
    BloomLevel,
    Difficulty,
    Question,
    QuestionType,
)
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.pagination import PaginatedResponse
from app.services.audit import AuditService

router = APIRouter()


class QuestionOut(BaseModel):
    id: str
    type: str
    text: str
    options: list[str] | None = None
    correctAnswers: list[str]
    explanation: str | None = None
    hint: str | None = None
    difficulty: str
    bloomLevel: str | None = None
    tags: list[str] = []
    marks: int
    negativeMarks: float = 0.0
    topic: str | None = None
    subjectId: str | None = None
    folderId: str | None = None
    isVerified: bool = False
    isAiGenerated: bool = False
    createdAt: str


class QuestionCreate(BaseModel):
    type: str = Field(pattern="^(mcq|true_false|fill_blank|paragraph|coding|image_based|multi_select)$")
    text: str = Field(min_length=1)
    options: list[str] | None = None
    correctAnswers: list[str] = Field(min_length=1)
    explanation: str | None = None
    hint: str | None = None
    difficulty: str = Field(pattern="^(easy|medium|hard)$")
    bloomLevel: str | None = None
    tags: list[str] = []
    marks: int = Field(default=1, ge=1)
    negativeMarks: float = 0.0
    topic: str | None = None
    subjectId: str | None = None
    folderId: str | None = None
    isVerified: bool = False


class QuestionUpdate(BaseModel):
    text: str | None = None
    options: list[str] | None = None
    correctAnswers: list[str] | None = None
    explanation: str | None = None
    hint: str | None = None
    difficulty: str | None = None
    bloomLevel: str | None = None
    tags: list[str] | None = None
    marks: int | None = None
    negativeMarks: float | None = None
    topic: str | None = None
    subjectId: str | None = None
    folderId: str | None = None
    isVerified: bool | None = None


def _question_out(q: Question) -> QuestionOut:
    return QuestionOut(
        id=str(q.id),
        type=q.type.value,
        text=q.text,
        options=q.options,
        correctAnswers=q.correct_answers,
        explanation=q.explanation,
        hint=q.hint,
        difficulty=q.difficulty.value,
        bloomLevel=q.bloom_level.value if q.bloom_level else None,
        tags=q.tags or [],
        marks=q.marks,
        negativeMarks=q.negative_marks,
        topic=q.topic,
        subjectId=str(q.subject_id) if q.subject_id else None,
        folderId=str(q.folder_id) if q.folder_id else None,
        isVerified=q.is_verified,
        isAiGenerated=q.is_ai_generated,
        createdAt=q.created_at.isoformat(),
    )


@router.get("", response_model=PaginatedResponse[QuestionOut], summary="List questions")
async def list_questions(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    question_type: str | None = None,
    difficulty: str | None = None,
    subject_id: str | None = None,
) -> PaginatedResponse[QuestionOut]:
    base = select(Question).where(Question.deleted_at.is_(None)).order_by(Question.created_at.desc())
    if search:
        base = base.where(Question.text.ilike(f"%{search}%"))
    if question_type:
        base = base.where(Question.type == QuestionType(question_type))
    if difficulty:
        base = base.where(Question.difficulty == Difficulty(difficulty))
    if subject_id:
        base = base.where(Question.subject_id == subject_id)

    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    result = await db.execute(base.limit(page_size).offset((page - 1) * page_size))
    items = [_question_out(q) for q in result.scalars().all()]
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(items=items, page=page, pageSize=page_size, total=total, totalPages=total_pages)


async def _get_question_or_404(db: AsyncSession, question_id: str) -> Question:
    result = await db.execute(
        select(Question).where(Question.id == question_id, Question.deleted_at.is_(None))
    )
    q = result.scalar_one_or_none()
    if q is None:
        raise NotFoundError("Question not found")
    return q


@router.get("/{question_id}", response_model=QuestionOut, summary="Question detail")
async def get_question(
    question_id: str,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuestionOut:
    return _question_out(await _get_question_or_404(db, question_id))


@router.post("", response_model=QuestionOut, status_code=status.HTTP_201_CREATED, summary="Create question")
async def create_question(
    body: QuestionCreate,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuestionOut:
    q = Question(
        type=QuestionType(body.type),
        text=body.text,
        options=body.options,
        correct_answers=body.correctAnswers,
        explanation=body.explanation,
        hint=body.hint,
        difficulty=Difficulty(body.difficulty),
        bloom_level=BloomLevel(body.bloomLevel) if body.bloomLevel else None,
        tags=body.tags,
        marks=body.marks,
        negative_marks=body.negativeMarks,
        topic=body.topic,
        subject_id=body.subjectId,
        folder_id=body.folderId,
        is_verified=body.isVerified,
        created_by=actor.id,
    )
    db.add(q)
    await db.flush()
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="question.create",
        entity_type="question",
        entity_id=str(q.id),
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    return _question_out(q)


@router.patch("/{question_id}", response_model=QuestionOut, summary="Update question")
async def update_question(
    question_id: str,
    body: QuestionUpdate,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuestionOut:
    q = await _get_question_or_404(db, question_id)
    updates = body.model_dump(exclude_unset=True, exclude_none=True)
    field_map = {
        "correctAnswers": "correct_answers",
        "negativeMarks": "negative_marks",
        "subjectId": "subject_id",
        "folderId": "folder_id",
        "isVerified": "is_verified",
        "bloomLevel": "bloom_level",
    }
    for k, v in updates.items():
        attr = field_map.get(k, k)
        if attr == "bloom_level":
            v = BloomLevel(v) if v else None
        if attr == "difficulty" and v:
            v = Difficulty(v)
        setattr(q, attr, v)
    await db.flush()
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="question.update",
        entity_type="question",
        entity_id=question_id,
        new_value=body.model_dump(mode="json", exclude_none=True),
    )
    await db.commit()
    return _question_out(q)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete question (soft)")
async def delete_question(
    question_id: str,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    from datetime import UTC, datetime

    q = await _get_question_or_404(db, question_id)
    q.deleted_at = datetime.now(UTC)
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="question.delete",
        entity_type="question",
        entity_id=question_id,
        old_value={"text": q.text[:200]},
    )
    await db.commit()