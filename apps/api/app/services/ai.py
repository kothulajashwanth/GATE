from abc import ABC, abstractmethod
from dataclasses import dataclass
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
    tags: list[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class AIProvider(ABC):
    """Abstract AI provider. Subclasses implement specific backends."""

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
    """Deterministic mock for development / testing."""

    async def generate_questions(self, *, prompt: str, count: int, difficulty: Optional[str] = None, question_type: Optional[str] = None, topic: Optional[str] = None, bloom_level: Optional[str] = None) -> list[AIQuestion]:
        qs = []
        for i in range(count):
            qs.append(AIQuestion(
                type=question_type or "mcq",
                text=f"[Mock] {prompt} — question {i + 1}",
                options=["A", "B", "C", "D"] if (question_type or "mcq") in ("mcq", "multi_select") else None,
                correct_answers=["A"],
                explanation="Mock explanation",
                hint="Mock hint",
                difficulty=difficulty or "medium",
                bloom_level=bloom_level or "understand",
                marks=1,
                negative_marks=0.0,
                topic=topic or "general",
                learning_outcome="Understand basic concept",
                tags=["mock", topic] if topic else ["mock"],
            ))
        return qs

    async def generate_exam_paper(self, *, topic: str, total_marks: int, duration_minutes: int, difficulty_distribution: dict[str, int], question_types: list[str]) -> list[AIQuestion]:
        qs = []
        for diff, cnt in difficulty_distribution.items():
            for i in range(cnt):
                qs.append(AIQuestion(
                    type=question_types[i % len(question_types)] if question_types else "mcq",
                    text=f"[Mock] {topic} question {len(qs) + 1}",
                    options=["A", "B", "C", "D"],
                    correct_answers=["A"],
                    explanation=f"Mock explanation for {topic}",
                    hint="Mock hint",
                    difficulty=diff,
                    bloom_level="apply",
                    marks=1,
                    topic=topic,
                    tags=["mock", topic],
                ))
        return qs

    async def improve_question(self, question: AIQuestion, instruction: str) -> AIQuestion:
        q = AIQuestion(
            type=question.type,
            text=f"[Improved] {question.text} ({instruction})",
            options=question.options,
            correct_answers=question.correct_answers,
            explanation=question.explanation,
            hint=question.hint,
            difficulty=question.difficulty,
            bloom_level=question.bloom_level,
            marks=question.marks,
            negative_marks=question.negative_marks,
            topic=question.topic,
            learning_outcome=question.learning_outcome,
            tags=question.tags + ["improved"],
        )
        return q

    async def generate_explanation(self, question: AIQuestion) -> str:
        return f"Mock explanation: {question.text}"

    async def generate_hint(self, question: AIQuestion) -> str:
        return "Mock hint: think step by step."

    async def generate_wrong_options(self, question: AIQuestion, count: int) -> list[str]:
        return [f"Wrong {i + 1}" for i in range(count)]

    async def classify_question(self, question: AIQuestion) -> dict[str, Any]:
        return {"topic": question.topic, "difficulty": question.difficulty, "bloom": question.bloom_level}

    async def detect_topic(self, question: AIQuestion) -> Optional[str]:
        return question.topic


class OpenAIProvider(AIProvider):
    """OpenAI GPT provider using function-calling / structured outputs."""

    def __init__(self) -> None:
        from openai import AsyncOpenAI
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    async def generate_questions(self, *, prompt: str, count: int, difficulty: Optional[str] = None, question_type: Optional[str] = None, topic: Optional[str] = None, bloom_level: Optional[str] = None) -> list[AIQuestion]:
        from pydantic import BaseModel, Field
        from typing import List, Optional as Opt

        class Q(BaseModel):
            type: str = Field(description="Question type: mcq, true_false, fill_blank, paragraph, coding, image_based, multi_select")
            text: str = Field(description="Question text")
            options: Opt[List[str]] = Field(default=None, description="Options for mcq/multi_select")
            correct_answers: List[str]
            explanation: Opt[str] = None
            hint: Opt[str] = None
            difficulty: str = Field(description="easy, medium, hard")
            bloom_level: Opt[str] = None
            marks: int = 1
            negative_marks: float = 0.0
            topic: Opt[str] = None
            learning_outcome: Opt[str] = None
            tags: List[str] = []

        class Response(BaseModel):
            questions: List[Q]

        sys = "You are an expert exam question author. Produce high-quality questions matching the requested specs. Return valid JSON."
        user = f"Generate {count} questions. Prompt: {prompt}. Difficulty: {difficulty or 'mixed'}. Type: {question_type or 'any'}. Topic: {topic or 'any'}. Bloom: {bloom_level or 'any'}."

        resp = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
            response_format=Response,
            temperature=0.7,
        )
        parsed = resp.choices[0].message.parsed
        return [AIQuestion(**q.model_dump()) for q in parsed.questions]

    async def generate_exam_paper(self, *, topic: str, total_marks: int, duration_minutes: int, difficulty_distribution: dict[str, int], question_types: list[str]) -> list[AIQuestion]:
        # Reuse generate_questions for each difficulty bucket
        qs = []
        for diff, cnt in difficulty_distribution.items():
            batch = await self.generate_questions(prompt=f"Exam paper on {topic}", count=cnt, difficulty=diff, question_type=question_types[0] if question_types else None, topic=topic)
            qs.extend(batch)
        return qs

    async def improve_question(self, question: AIQuestion, instruction: str) -> AIQuestion:
        # Single-question improvement
        return await self._single_call(
            "Improve this question per the instruction. Return the full question JSON.",
            question,
            f"Instruction: {instruction}",
        )

    async def generate_explanation(self, question: AIQuestion) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Generate a clear, concise explanation for the given question and correct answer."},
                {"role": "user", "content": f"Question: {question.text}\nCorrect: {question.correct_answers}"},
            ],
            temperature=0.3,
        )
        return resp.choices[0].message.content or ""

    async def generate_hint(self, question: AIQuestion) -> str:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Generate a helpful hint that guides the student without giving the answer."},
                {"role": "user", "content": f"Question: {question.text}"},
            ],
            temperature=0.4,
        )
        return resp.choices[0].message.content or ""

    async def generate_wrong_options(self, question: AIQuestion, count: int) -> list[str]:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": f"Generate {count} plausible but incorrect options for an MCQ. Return JSON array of strings."},
                {"role": "user", "content": f"Question: {question.text}\nCorrect: {question.correct_answers}"},
            ],
            temperature=0.6,
            response_format={"type": "json_object"},
        )
        import json
        data = json.loads(resp.choices[0].message.content or "{}")
        return data.get("options", [])[:count]

    async def classify_question(self, question: AIQuestion) -> dict[str, Any]:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Classify the question: topic, difficulty, Bloom level. Return JSON."},
                {"role": "user", "content": f"Question: {question.text}"},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        import json
        return json.loads(resp.choices[0].message.content or "{}")

    async def detect_topic(self, question: AIQuestion) -> Optional[str]:
        resp = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Extract the main topic/keyword from the question. Return plain text."},
                {"role": "user", "content": f"Question: {question.text}"},
            ],
            temperature=0.1,
        )
        return resp.choices[0].message.content

    async def _single_call(self, instruction: str, question: AIQuestion, extra: str) -> AIQuestion:
        from pydantic import BaseModel, Field
        from typing import List, Optional as Opt

        class Q(BaseModel):
            type: str
            text: str
            options: Opt[List[str]] = None
            correct_answers: List[str]
            explanation: Opt[str] = None
            hint: Opt[str] = None
            difficulty: str
            bloom_level: Opt[str] = None
            marks: int = 1
            negative_marks: float = 0.0
            topic: Opt[str] = None
            learning_outcome: Opt[str] = None
            tags: List[str] = []

        class Response(BaseModel):
            question: Q

        sys = instruction
        user = f"Question: {question.text}\nType: {question.type}\nOptions: {question.options}\nCorrect: {question.correct_answers}\nExtra: {extra}"

        resp = await self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[{"role": "system", "content": sys}, {"role": "user", "content": user}],
            response_format=Response,
            temperature=0.4,
        )
        q = resp.choices[0].message.parsed.question
        return AIQuestion(**q.model_dump())


class GeminiProvider(AIProvider):
    """Google Gemini provider (stub — similar structure to OpenAI)."""

    def __init__(self) -> None:
        import google.generativeai as genai
        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    async def generate_questions(self, *, prompt: str, count: int, difficulty: Optional[str] = None, question_type: Optional[str] = None, topic: Optional[str] = None, bloom_level: Optional[str] = None) -> list[AIQuestion]:
        # Placeholder: implement with structured output schema
        return []

    async def generate_exam_paper(self, *, topic: str, total_marks: int, duration_minutes: int, difficulty_distribution: dict[str, int], question_types: list[str]) -> list[AIQuestion]:
        return []

    async def improve_question(self, question: AIQuestion, instruction: str) -> AIQuestion:
        return question

    async def generate_explanation(self, question: AIQuestion) -> str:
        return ""

    async def generate_hint(self, question: AIQuestion) -> str:
        return ""

    async def generate_wrong_options(self, question: AIQuestion, count: int) -> list[str]:
        return []

    async def classify_question(self, question: AIQuestion) -> dict[str, Any]:
        return {}

    async def detect_topic(self, question: AIQuestion) -> Optional[str]:
        return None


def get_ai_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "openai" and settings.openai_api_key:
        return OpenAIProvider()
    if settings.ai_provider == "gemini" and settings.gemini_api_key:
        return GeminiProvider()
    return MockProvider()