from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.db.models.user import Role, User
from app.db.session import get_db
from app.services.ai import get_ai_provider

router = APIRouter()


class GenerateQuestionsRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    count: int = Field(ge=1, le=20, default=5)
    difficulty: str | None = Field(default=None, pattern="^(easy|medium|hard)$")
    question_type: str | None = Field(default=None, pattern="^(mcq|true_false|fill_blank|paragraph|coding|image_based|multi_select)$")
    topic: str | None = None
    bloom_level: str | None = Field(default=None, pattern="^(remember|understand|apply|analyze|evaluate|create)$")


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
    learning_outcome: str | None = None
    tags: list[str] = []


class ImproveQuestionRequest(BaseModel):
    question: AIQuestionOut
    instruction: str = Field(min_length=1, max_length=1000)


class GenerateExamPaperRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=200)
    total_marks: int = Field(ge=1, le=500, default=100)
    duration_minutes: int = Field(ge=1, le=300, default=120)
    difficulty_distribution: dict[str, int] = Field(default_factory=lambda: {"easy": 3, "medium": 5, "hard": 2})
    question_types: list[str] = Field(default_factory=lambda: ["mcq", "true_false", "fill_blank"])


@router.post("/generate-questions", response_model=list[AIQuestionOut], summary="Generate questions from prompt")
async def generate_questions(
    body: GenerateQuestionsRequest,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AIQuestionOut]:
    provider = get_ai_provider()
    questions = await provider.generate_questions(
        prompt=body.prompt,
        count=body.count,
        difficulty=body.difficulty,
        question_type=body.question_type,
        topic=body.topic,
        bloom_level=body.bloom_level,
    )
    return [AIQuestionOut(**q.__dict__) for q in questions]


@router.post("/improve-question", response_model=AIQuestionOut, summary="Improve an existing question")
async def improve_question(
    body: ImproveQuestionRequest,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AIQuestionOut:
    provider = get_ai_provider()
    from app.services.ai import AIQuestion

    q = AIQuestion(**body.question.model_dump())
    improved = await provider.improve_question(q, body.instruction)
    return AIQuestionOut(**improved.__dict__)


@router.post("/generate-explanation", response_model=dict, summary="Generate explanation for a question")
async def generate_explanation(
    body: AIQuestionOut,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    provider = get_ai_provider()
    from app.services.ai import AIQuestion

    q = AIQuestion(**body.model_dump())
    explanation = await provider.generate_explanation(q)
    return {"explanation": explanation}


@router.post("/generate-hint", response_model=dict, summary="Generate hint for a question")
async def generate_hint(
    body: AIQuestionOut,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    provider = get_ai_provider()
    from app.services.ai import AIQuestion

    q = AIQuestion(**body.model_dump())
    hint = await provider.generate_hint(q)
    return {"hint": hint}


@router.post("/generate-wrong-options", response_model=dict, summary="Generate plausible wrong options")
async def generate_wrong_options(
    body: AIQuestionOut,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    count: int = 3,
) -> dict:
    provider = get_ai_provider()
    from app.services.ai import AIQuestion

    q = AIQuestion(**body.model_dump())
    options = await provider.generate_wrong_options(q, count)
    return {"options": options}


@router.post("/generate-exam-paper", response_model=list[AIQuestionOut], summary="Generate a full exam paper")
async def generate_exam_paper(
    body: GenerateExamPaperRequest,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AIQuestionOut]:
    provider = get_ai_provider()
    questions = await provider.generate_exam_paper(
        topic=body.topic,
        total_marks=body.total_marks,
        duration_minutes=body.duration_minutes,
        difficulty_distribution=body.difficulty_distribution,
        question_types=body.question_types,
    )
    return [AIQuestionOut(**q.__dict__) for q in questions]