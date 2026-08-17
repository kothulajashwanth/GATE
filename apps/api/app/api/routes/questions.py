from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import require_roles
from app.core.errors import NotFoundError
from app.db.models.question import (
    BloomLevel,
    Difficulty,
    Question,
    QuestionOption,
    QuestionType,
    QuestionVersion,
)
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.pagination import PaginatedResponse
from app.services.audit import AuditService
from app.services.question_service import QuestionService

router = APIRouter()


class QuestionVersionOut(BaseModel):
    version: int
    changeSummary: str | None = None
    createdAt: str


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
    sourceFileId: str | None = None
    isVerified: bool = False
    isAiGenerated: bool = False
    version: int = 1
    versions: list[QuestionVersionOut] = []
    createdAt: str


class QuestionCreate(BaseModel):
    type: str = Field(default="mcq", pattern="^(mcq|true_false|fill_blank|paragraph|coding|image_based|multi_select)$")
    text: str = Field(min_length=1)
    options: list[str] | None = None
    correctAnswers: list[str] = Field(min_length=1)
    explanation: str | None = None
    hint: str | None = None
    difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")
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
    changeSummary: str | None = None


import logging

logger = logging.getLogger("app")


def _question_out(q: Question) -> QuestionOut:
    versions_out = [
        QuestionVersionOut(
            id=str(v.id),
            questionId=str(v.question_id),
            version=v.version,
            text=v.text,
            options=v.options,
            correctAnswers=v.correct_answers,
            explanation=v.explanation,
            changedBy=str(v.changed_by) if v.changed_by else None,
            createdAt=v.created_at.isoformat() if v.created_at else datetime.now(UTC).isoformat(),
        )
        for v in getattr(q, "versions", [])
    ]
    return QuestionOut(
        id=str(q.id),
        type=q.type.value if hasattr(q.type, "value") else (str(q.type) if q.type else "mcq"),
        text=q.text,
        options=q.options,
        correctAnswers=q.correct_answers,
        explanation=q.explanation,
        hint=q.hint,
        difficulty=q.difficulty.value if hasattr(q.difficulty, "value") else (str(q.difficulty) if q.difficulty else "medium"),
        bloomLevel=q.bloom_level.value if hasattr(q.bloom_level, "value") else (str(q.bloom_level) if q.bloom_level else None),
        tags=q.tags or [],
        marks=q.marks,
        negativeMarks=q.negative_marks,
        topic=q.topic,
        subjectId=str(q.subject_id) if q.subject_id else None,
        folderId=str(q.folder_id) if q.folder_id else None,
        sourceFileId=str(q.source_file_id) if q.source_file_id else None,
        isVerified=q.is_verified,
        isAiGenerated=q.is_ai_generated,
        version=q.version,
        versions=versions_out,
        createdAt=q.created_at.isoformat() if q.created_at else datetime.now(UTC).isoformat(),
    )


@router.get("", response_model=PaginatedResponse[QuestionOut], summary="List questions")
async def list_questions(
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    question_type: str | None = None,
    difficulty: str | None = None,
    subject_id: str | None = None,
    topic: str | None = None,
    is_verified: bool | None = None,
) -> PaginatedResponse[QuestionOut]:
    logger.info(f"[QUESTIONS] REQUEST RECEIVED: page={page}, page_size={page_size}")
    logger.info(f"[QUESTIONS] AUTHENTICATION PASSED: user_id={actor.id}, email={actor.email}, role={actor.role}")
    logger.info("[QUESTIONS] STARTING DATABASE QUERY")
    base = select(Question).where(Question.deleted_at.is_(None)).options(selectinload(Question.versions)).order_by(Question.created_at.desc())
    if search:
        base = base.where(Question.text.ilike(f"%{search}%"))
    if question_type:
        base = base.where(Question.type == QuestionType(question_type.lower()))
    if difficulty:
        base = base.where(Question.difficulty == Difficulty(difficulty.lower()))
    if subject_id:
        base = base.where(Question.subject_id == subject_id)
    if topic:
        base = base.where(Question.topic.ilike(f"%{topic}%"))
    if is_verified is not None:
        base = base.where(Question.is_verified == is_verified)

    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    result = await db.execute(base.limit(page_size).offset((page - 1) * page_size))
    items = [_question_out(q) for q in result.scalars().all()]
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(items=items, page=page, pageSize=page_size, total=total, totalPages=total_pages)


async def _get_question_or_404(db: AsyncSession, question_id: str) -> Question:
    result = await db.execute(
        select(Question)
        .where(Question.id == question_id, Question.deleted_at.is_(None))
        .options(selectinload(Question.versions), selectinload(Question.options_rel))
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
        type=QuestionType(body.type.lower()),
        text=body.text,
        options=body.options,
        correct_answers=body.correctAnswers,
        explanation=body.explanation,
        hint=body.hint,
        difficulty=Difficulty(body.difficulty.lower()),
        bloom_level=BloomLevel(body.bloomLevel.lower()) if body.bloomLevel else None,
        tags=body.tags,
        marks=body.marks,
        negative_marks=body.negativeMarks,
        topic=body.topic,
        subject_id=body.subjectId,
        folder_id=body.folderId,
        is_verified=body.isVerified,
        created_by=actor.id,
        version=1,
    )
    db.add(q)
    await db.flush()

    # Create QuestionOption records
    if body.options:
        for idx, opt_text in enumerate(body.options):
            opt_letter = chr(65 + idx)
            is_correct = opt_letter in body.correctAnswers or str(idx) in body.correctAnswers or opt_text in body.correctAnswers
            q_opt = QuestionOption(
                question_id=q.id,
                option_text=opt_text,
                is_correct=is_correct,
                display_order=idx + 1,
            )
            db.add(q_opt)

    # Create initial QuestionVersion
    qv = QuestionVersion(
        question_id=q.id,
        version=1,
        snapshot=body.model_dump(mode="json"),
        change_summary="Initial manual creation",
        changed_by=actor.id,
    )
    db.add(qv)

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="QUESTION_CREATED",
        entity_type="question",
        entity_id=str(q.id),
        new_value=body.model_dump(mode="json"),
    )
    await db.commit()
    return _question_out(await _get_question_or_404(db, str(q.id)))


@router.put("/{question_id}", response_model=QuestionOut, summary="Update question")
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
    change_summary = updates.pop("changeSummary", None) or "Updated question profile"

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
            v = BloomLevel(v.lower()) if v else None
        elif attr == "difficulty" and v:
            v = Difficulty(v.lower())
        elif attr == "type" and v:
            v = QuestionType(v.lower())
        setattr(q, attr, v)

    service = QuestionService(db)
    await service.create_question_version(q, actor, change_summary=change_summary)

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="QUESTION_UPDATED",
        entity_type="question",
        entity_id=question_id,
        new_value=body.model_dump(mode="json", exclude_none=True),
    )
    await db.commit()
    return _question_out(await _get_question_or_404(db, question_id))


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
        action="QUESTION_DELETED",
        entity_type="question",
        entity_id=question_id,
        old_value={"text": q.text[:200]},
    )
    await db.commit()


class BulkApproveRequest(BaseModel):
    question_ids: list[str]


@router.post("/approve-bulk", summary="Approve multiple questions")
async def bulk_approve_questions(
    body: BulkApproveRequest,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = QuestionService(db)
    approved_count = await service.approve_questions(body.question_ids, actor)
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="QUESTIONS_BULK_APPROVED",
        entity_type="question",
        entity_id="bulk",
        new_value={"approved_count": approved_count},
    )
    await db.commit()
    return {"status": "SUCCESS", "approved_count": approved_count}


@router.post("/{question_id}/approve", response_model=QuestionOut, summary="Approve a single question")
async def approve_question(
    question_id: str,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> QuestionOut:
    service = QuestionService(db)
    await service.approve_questions([question_id], actor)
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="QUESTION_APPROVED",
        entity_type="question",
        entity_id=question_id,
        new_value={"is_verified": True},
    )
    await db.commit()
    return _question_out(await _get_question_or_404(db, question_id))