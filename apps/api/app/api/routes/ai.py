from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
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
from app.services.ai import AIQuestion, get_ai_provider
from app.services.audit import AuditService
from app.services.blueprint_service import BlueprintRule, BlueprintService
from app.services.document_parser import normalize_text

router = APIRouter()


class GenerateQuestionsRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    count: int = Field(ge=1, le=50, default=5)
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")
    question_type: str | None = Field(default=None, pattern="^(mcq|true_false|fill_blank|paragraph|coding|image_based|multi_select)$")
    topic: str | None = None
    subject_id: str | None = None
    bloom_level: str | None = Field(default=None, pattern="^(remember|understand|apply|analyze|evaluate|create)$")
    source_file_id: str | None = None


class AIQuestionOut(BaseModel):
    type: str
    text: str
    options: list[str] | None = None
    correct_answers: list[str]
    explanation: str | None = None
    hint: str | None = None
    difficulty: str
    bloom_level: str | None = None
    marks: int = 1
    negative_marks: float = 0.0
    topic: str | None = None
    subject_id: str | None = None
    is_duplicate: bool = False
    status: str = "NEEDS_REVIEW"


class ApproveQuestionItem(BaseModel):
    type: str = "mcq"
    text: str
    options: list[str] | None = None
    correctAnswers: list[str]
    explanation: str | None = None
    difficulty: str = "medium"
    bloomLevel: str | None = None
    marks: int = 1
    negativeMarks: float = 0.0
    topic: str | None = None
    subjectId: str | None = None


class BulkApproveRequest(BaseModel):
    questions: list[ApproveQuestionItem]


class BlueprintRuleSchema(BaseModel):
    subject_id: str | None = None
    topic: str | None = None
    question_type: str | None = None
    difficulty: str | None = None
    bloom_level: str | None = None
    count: int = Field(ge=1, default=1)
    marks: int = Field(ge=1, default=1)


class BlueprintRequest(BaseModel):
    exam_id: str | None = None
    rules: list[BlueprintRuleSchema]


@router.post("/generate-questions", response_model=list[AIQuestionOut], summary="Generate questions using AI provider")
async def generate_questions(
    body: GenerateQuestionsRequest,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AIQuestionOut]:
    provider = get_ai_provider()
    await AuditService.log(
        db, actor=actor, request=request, action="AI_GENERATION_STARTED", entity_type="ai_generator", new_value=body.model_dump(mode="json")
    )

    questions = await provider.generate_questions(
        prompt=body.prompt,
        count=body.count,
        difficulty=body.difficulty,
        question_type=body.question_type,
        topic=body.topic,
        bloom_level=body.bloom_level,
    )

    # Duplicate check against existing PostgreSQL questions
    existing_db = (await db.execute(select(Question.text).where(Question.deleted_at.is_(None)))).scalars().all()
    existing_norm = {normalize_text(t) for t in existing_db if t}

    out: list[AIQuestionOut] = []
    for q in questions:
        norm = normalize_text(q.text)
        is_dup = norm in existing_norm
        out.append(
            AIQuestionOut(
                type=q.type,
                text=q.text,
                options=q.options,
                correct_answers=q.correct_answers,
                explanation=q.explanation,
                hint=q.hint,
                difficulty=q.difficulty,
                bloom_level=q.bloom_level,
                marks=q.marks,
                negative_marks=q.negative_marks,
                topic=q.topic,
                subject_id=body.subject_id,
                is_duplicate=is_dup,
                status="NEEDS_REVIEW",
            )
        )

    await AuditService.log(
        db, actor=actor, request=request, action="AI_GENERATION_COMPLETED", entity_type="ai_generator", new_value={"count": len(out)}
    )
    await db.commit()
    return out


@router.post("/questions/approve", response_model=dict, summary="Approve AI-generated questions into Question Bank")
async def approve_questions(
    body: BulkApproveRequest,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    created_ids = []
    for item in body.questions:
        try:
            q_type = QuestionType(item.type.lower())
        except ValueError:
            q_type = QuestionType.MCQ

        try:
            diff = Difficulty(item.difficulty.lower())
        except ValueError:
            diff = Difficulty.MEDIUM

        bloom = BloomLevel(item.bloomLevel.lower()) if item.bloomLevel else None

        question = Question(
            type=q_type,
            text=item.text,
            options=item.options,
            correct_answers=item.correctAnswers,
            explanation=item.explanation,
            difficulty=diff,
            bloom_level=bloom,
            marks=item.marks,
            negative_marks=item.negativeMarks,
            topic=item.topic,
            subject_id=item.subjectId,
            is_verified=True,
            is_ai_generated=True,
            created_by=actor.id,
            version=1,
        )
        db.add(question)
        await db.flush()

        if item.options:
            for idx, opt_text in enumerate(item.options):
                opt_letter = chr(65 + idx)
                is_correct = opt_letter in item.correctAnswers or str(idx) in item.correctAnswers or opt_text in item.correctAnswers
                db.add(QuestionOption(question_id=question.id, option_text=opt_text, is_correct=is_correct, display_order=idx + 1))

        db.add(QuestionVersion(question_id=question.id, version=1, snapshot=item.model_dump(mode="json"), change_summary="Approved AI generated question", changed_by=actor.id))
        created_ids.append(str(question.id))

    await AuditService.log(
        db, actor=actor, request=request, action="QUESTION_AI_APPROVED", entity_type="question", new_value={"approved_count": len(created_ids)}
    )
    await db.commit()
    return {"status": "APPROVED", "approved_count": len(created_ids), "question_ids": created_ids}


@router.post("/blueprints/check-availability", summary="Check Question Bank availability for Blueprint rules")
async def check_blueprint_availability(
    body: BlueprintRequest,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = BlueprintService(db)
    rules = [BlueprintRule(**r.model_dump()) for r in body.rules]
    res = await service.check_availability(rules)
    return {
        "total_requested": res.total_requested,
        "total_available": res.total_available,
        "total_gap": res.total_gap,
        "rules_availability": res.rules_availability,
    }


@router.post("/blueprints/fill-gaps", summary="Generate missing questions for blueprint gaps using AI")
async def fill_blueprint_gaps(
    body: BlueprintRequest,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = BlueprintService(db)
    rules = [BlueprintRule(**r.model_dump()) for r in body.rules]
    generated = await service.fill_gaps_with_ai(rules, actor)

    await AuditService.log(
        db, actor=actor, request=request, action="BLUEPRINT_CREATED", entity_type="blueprint", new_value={"generated_gaps": len(generated)}
    )
    await db.commit()
    return {"generated_count": len(generated), "question_ids": [str(q.id) for q in generated]}


@router.post("/blueprints/assemble-exam", summary="Assemble approved questions from Question Bank into Exam")
async def assemble_exam_blueprint(
    body: BlueprintRequest,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    if not body.exam_id:
        return {"error": "exam_id is required"}

    service = BlueprintService(db)
    rules = [BlueprintRule(**r.model_dump()) for r in body.rules]
    links = await service.assemble_exam_from_blueprint(exam_id=body.exam_id, rules=rules)

    await AuditService.log(
        db, actor=actor, request=request, action="EXAM_ASSEMBLED", entity_type="exam", entity_id=body.exam_id, new_value={"assembled_count": len(links)}
    )
    await db.commit()
    return {"exam_id": body.exam_id, "assembled_count": len(links)}