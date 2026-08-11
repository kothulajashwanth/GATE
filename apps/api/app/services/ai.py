import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

from app.core.config import get_settings


@dataclass
class AIQuestion:
    type: str
    text: str
    options: Optional[list[str]]
    correct_answers: list[str]
    explanation: Optional[str]
    hint: Optional[str]
    difficulty: str
    bloom_level: Optional[str]
    marks: int = 1
    negative_marks: float = 0.0
    topic: Optional[str] = None
    learning_outcome: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    source_reference: Optional[str] = None
    is_duplicate: bool = False
    status: str = "NEEDS_REVIEW"

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class AIProvider(ABC):
    """Abstract AI provider interface."""

    @abstractmethod
    async def generate_questions(
        self,
        *,
        prompt: str,
        count: int,
        difficulty: Optional[str] = None,
        question_type: Optional[str] = None,
        topic: Optional[str] = None,
        bloom_level: Optional[str] = None,
        source_text: Optional[str] = None,
    ) -> list[AIQuestion]:
        pass

    @abstractmethod
    async def generate_exam_paper(
        self,
        *,
        topic: str,
        total_marks: int,
        duration_minutes: int,
        difficulty_distribution: dict[str, int],
        question_types: list[str],
    ) -> list[AIQuestion]:
        pass

    @abstractmethod
    async def improve_question(self, question: AIQuestion, instruction: str) -> AIQuestion:
        pass

    @abstractmethod
    async def generate_explanation(self, question: AIQuestion) -> str:
        pass

    @abstractmethod
    async def generate_hint(self, question: AIQuestion) -> str:
        pass

    @abstractmethod
    async def generate_wrong_options(self, question: AIQuestion, count: int) -> list[str]:
        pass

    @abstractmethod
    async def classify_question(self, question: AIQuestion) -> dict[str, Any]:
        pass

    @abstractmethod
    async def detect_topic(self, question: AIQuestion) -> Optional[str]:
        pass


class MockProvider(AIProvider):
    """Deterministic mock provider for development and automated testing."""

    async def generate_questions(
        self,
        *,
        prompt: str,
        count: int,
        difficulty: Optional[str] = None,
        question_type: Optional[str] = None,
        topic: Optional[str] = None,
        bloom_level: Optional[str] = None,
        source_text: Optional[str] = None,
    ) -> list[AIQuestion]:
        qs = []
        diffs = ["easy", "medium", "hard"]
        blooms = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
        q_type = (question_type or "mcq").lower()

        for i in range(count):
            cur_diff = (difficulty or diffs[i % len(diffs)]).lower()
            cur_bloom = (bloom_level or blooms[i % len(blooms)]).lower()
            q_text = f"[AI Generated] {prompt} — Question #{i + 1}"
            opts = ["Option A", "Option B", "Option C", "Option D"] if q_type in ("mcq", "multi_select") else None
            ans = ["A"] if q_type == "mcq" else ["A", "B"] if q_type == "multi_select" else ["True"] if q_type == "true_false" else ["Answer"]

            qs.append(
                AIQuestion(
                    type=q_type,
                    text=q_text,
                    options=opts,
                    correct_answers=ans,
                    explanation=f"AI Generated explanation for question #{i + 1}",
                    hint="Consider fundamental concepts.",
                    difficulty=cur_diff,
                    bloom_level=cur_bloom,
                    marks=2 if cur_diff == "hard" else 1,
                    negative_marks=0.0,
                    topic=topic or "Computer Science",
                    learning_outcome=f"Mastery of {topic or 'concept'}",
                    tags=["ai-generated", cur_diff, cur_bloom],
                    source_reference="Source Material Chunk #1" if source_text else None,
                    status="NEEDS_REVIEW",
                )
            )
        return qs

    async def generate_exam_paper(
        self,
        *,
        topic: str,
        total_marks: int,
        duration_minutes: int,
        difficulty_distribution: dict[str, int],
        question_types: list[str],
    ) -> list[AIQuestion]:
        qs = []
        for diff, cnt in difficulty_distribution.items():
            for i in range(cnt):
                qs.append(
                    AIQuestion(
                        type=question_types[len(qs) % len(question_types)] if question_types else "mcq",
                        text=f"[Exam Paper] {topic} {diff.upper()} Question #{len(qs) + 1}",
                        options=["Option A", "Option B", "Option C", "Option D"],
                        correct_answers=["A"],
                        explanation=f"Explanation for {topic}",
                        hint="Think carefully.",
                        difficulty=diff.lower(),
                        bloom_level="apply",
                        marks=2 if diff.lower() == "hard" else 1,
                        topic=topic,
                        tags=["exam-paper", diff.lower()],
                    )
                )
        return qs

    async def improve_question(self, question: AIQuestion, instruction: str) -> AIQuestion:
        return AIQuestion(
            type=question.type,
            text=f"[Improved AI] {question.text} ({instruction})",
            options=question.options,
            correct_answers=question.correct_answers,
            explanation=f"Regenerated explanation ({instruction})",
            hint=question.hint,
            difficulty=question.difficulty,
            bloom_level=question.bloom_level,
            marks=question.marks,
            negative_marks=question.negative_marks,
            topic=question.topic,
            learning_outcome=question.learning_outcome,
            tags=question.tags + ["regenerated"],
            status="NEEDS_REVIEW",
        )

    async def generate_explanation(self, question: AIQuestion) -> str:
        return f"AI Generated Explanation: The correct answer is {question.correct_answers[0]}."

    async def generate_hint(self, question: AIQuestion) -> str:
        return "AI Hint: Recall core principles."

    async def generate_wrong_options(self, question: AIQuestion, count: int) -> list[str]:
        return [f"Plausible Distractor #{i + 1}" for i in range(count)]

    async def classify_question(self, question: AIQuestion) -> dict[str, Any]:
        return {"topic": question.topic or "General", "difficulty": question.difficulty, "bloom": question.bloom_level or "understand"}

    async def detect_topic(self, question: AIQuestion) -> Optional[str]:
        return question.topic or "General"


class OpenAIProvider(AIProvider):
    """OpenAI GPT Provider using structured JSON outputs."""

    def __init__(self) -> None:
        from openai import AsyncOpenAI
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    async def generate_questions(
        self,
        *,
        prompt: str,
        count: int,
        difficulty: Optional[str] = None,
        question_type: Optional[str] = None,
        topic: Optional[str] = None,
        bloom_level: Optional[str] = None,
        source_text: Optional[str] = None,
    ) -> list[AIQuestion]:
        from pydantic import BaseModel, Field

        class QSchema(BaseModel):
            type: str = Field(description="mcq, true_false, fill_blank, paragraph, coding, multi_select")
            text: str
            options: Optional[list[str]] = None
            correct_answers: list[str]
            explanation: Optional[str] = None
            hint: Optional[str] = None
            difficulty: str = Field(description="easy, medium, hard")
            bloom_level: Optional[str] = Field(description="remember, understand, apply, analyze, evaluate, create")
            marks: int = 1
            negative_marks: float = 0.0
            topic: Optional[str] = None

        class ResponseSchema(BaseModel):
            questions: list[QSchema]

        sys_prompt = (
            "You are an expert college examination author. Generate high quality exam questions matching requested specs. "
            "Return structured JSON format adhering to the response schema."
        )
        user_prompt = (
            f"Generate {count} questions. Prompt instruction: {prompt}. "
            f"Difficulty: {difficulty or 'mixed'}. Type: {question_type or 'mcq'}. Topic: {topic or 'general'}. "
            f"Bloom Level: {bloom_level or 'understand'}. "
            f"{f'Source text: {source_text[:2000]}' if source_text else ''}"
        )

        resp = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}],
            response_format=ResponseSchema,
            temperature=0.7,
        )
        parsed = resp.choices[0].message.parsed
        return [AIQuestion(**q.model_dump()) for q in parsed.questions]

    async def generate_exam_paper(self, *, topic: str, total_marks: int, duration_minutes: int, difficulty_distribution: dict[str, int], question_types: list[str]) -> list[AIQuestion]:
        qs = []
        for diff, cnt in difficulty_distribution.items():
            batch = await self.generate_questions(prompt=f"Exam paper for {topic}", count=cnt, difficulty=diff, question_type=question_types[0] if question_types else "mcq", topic=topic)
            qs.extend(batch)
        return qs

    async def improve_question(self, question: AIQuestion, instruction: str) -> AIQuestion:
        qs = await self.generate_questions(prompt=f"Improve question: {question.text}. Instruction: {instruction}", count=1, difficulty=question.difficulty, question_type=question.type, topic=question.topic)
        return qs[0] if qs else question

    async def generate_explanation(self, question: AIQuestion) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": "Explain the answer."}, {"role": "user", "content": f"Question: {question.text}"}],
        )
        return resp.choices[0].message.content or ""

    async def generate_hint(self, question: AIQuestion) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": "Generate hint."}, {"role": "user", "content": f"Question: {question.text}"}],
        )
        return resp.choices[0].message.content or ""

    async def generate_wrong_options(self, question: AIQuestion, count: int) -> list[str]:
        return [f"Wrong Option #{i+1}" for i in range(count)]

    async def classify_question(self, question: AIQuestion) -> dict[str, Any]:
        return {"topic": question.topic, "difficulty": question.difficulty, "bloom": question.bloom_level}

    async def detect_topic(self, question: AIQuestion) -> Optional[str]:
        return question.topic


class GeminiProvider(AIProvider):
    """Google Gemini Provider implementation."""

    def __init__(self) -> None:
        import google.generativeai as genai
        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    async def generate_questions(
        self,
        *,
        prompt: str,
        count: int,
        difficulty: Optional[str] = None,
        question_type: Optional[str] = None,
        topic: Optional[str] = None,
        bloom_level: Optional[str] = None,
        source_text: Optional[str] = None,
    ) -> list[AIQuestion]:
        full_prompt = (
            f"Generate {count} exam questions as JSON array. Prompt: {prompt}. Difficulty: {difficulty or 'medium'}. "
            f"Type: {question_type or 'mcq'}. Topic: {topic or 'general'}. Bloom Level: {bloom_level or 'understand'}. "
            "JSON structure per item: {\"type\": \"mcq\", \"text\": \"...\", \"options\": [\"A\",\"B\",\"C\",\"D\"], \"correct_answers\": [\"A\"], \"explanation\": \"...\", \"difficulty\": \"medium\", \"bloom_level\": \"understand\", \"marks\": 1}"
        )
        res = self.model.generate_content(full_prompt)
        text = res.text or ""

        # Extract JSON array from output
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            try:
                items = json.loads(json_match.group(0))
                return [
                    AIQuestion(
                        type=item.get("type", "mcq"),
                        text=item.get("text", "Generated Question"),
                        options=item.get("options", ["A", "B", "C", "D"]),
                        correct_answers=item.get("correct_answers", ["A"]),
                        explanation=item.get("explanation"),
                        hint=item.get("hint"),
                        difficulty=item.get("difficulty", "medium").lower(),
                        bloom_level=item.get("bloom_level", "understand").lower(),
                        marks=item.get("marks", 1),
                        topic=topic,
                    )
                    for item in items
                ]
            except Exception:
                pass

        # Fallback to mock if parsing fails
        mock = MockProvider()
        return await mock.generate_questions(prompt=prompt, count=count, difficulty=difficulty, question_type=question_type, topic=topic, bloom_level=bloom_level)

    async def generate_exam_paper(self, *, topic: str, total_marks: int, duration_minutes: int, difficulty_distribution: dict[str, int], question_types: list[str]) -> list[AIQuestion]:
        mock = MockProvider()
        return await mock.generate_exam_paper(topic=topic, total_marks=total_marks, duration_minutes=duration_minutes, difficulty_distribution=difficulty_distribution, question_types=question_types)

    async def improve_question(self, question: AIQuestion, instruction: str) -> AIQuestion:
        mock = MockProvider()
        return await mock.improve_question(question, instruction)

    async def generate_explanation(self, question: AIQuestion) -> str:
        return f"Gemini Explanation: {question.text}"

    async def generate_hint(self, question: AIQuestion) -> str:
        return "Gemini Hint: Review fundamental definitions."

    async def generate_wrong_options(self, question: AIQuestion, count: int) -> list[str]:
        return [f"Gemini Option #{i+1}" for i in range(count)]

    async def classify_question(self, question: AIQuestion) -> dict[str, Any]:
        return {"topic": question.topic, "difficulty": question.difficulty, "bloom": question.bloom_level}

    async def detect_topic(self, question: AIQuestion) -> Optional[str]:
        return question.topic


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "openai" and settings.openai_api_key:
        try:
            return OpenAIProvider()
        except Exception:
            pass
    if settings.ai_provider == "gemini" and settings.gemini_api_key:
        try:
            return GeminiProvider()
        except Exception:
            pass
    return MockProvider()