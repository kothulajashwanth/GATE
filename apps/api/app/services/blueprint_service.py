from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.db.models.exam import Exam, ExamQuestion
from app.db.models.question import BloomLevel, Difficulty, Question, QuestionType
from app.db.models.user import User
from app.services.ai import get_ai_provider


@dataclass
class BlueprintRule:
    subject_id: str | None = None
    topic: str | None = None
    question_type: str | None = None
    difficulty: str | None = None
    bloom_level: str | None = None
    count: int = 1
    marks: int = 1


@dataclass
class AvailabilityResult:
    total_requested: int
    total_available: int
    total_gap: int
    rules_availability: list[dict[str, Any]] = field(default_factory=list)


class BlueprintService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def check_availability(self, rules: list[BlueprintRule]) -> AvailabilityResult:
        """Check existing approved questions in PostgreSQL Question Bank for each blueprint rule."""
        availability_list: list[dict[str, Any]] = []
        total_req = 0
        total_avail = 0
        total_gap = 0

        for idx, rule in enumerate(rules):
            total_req += rule.count

            stmt = select(func.count(Question.id)).where(Question.deleted_at.is_(None), Question.is_verified.is_(True))
            if rule.subject_id:
                stmt = stmt.where(Question.subject_id == rule.subject_id)
            if rule.topic:
                stmt = stmt.where(Question.topic.ilike(f"%{rule.topic}%"))
            if rule.difficulty:
                stmt = stmt.where(Question.difficulty == Difficulty(rule.difficulty.lower()))
            if rule.bloom_level:
                stmt = stmt.where(Question.bloom_level == BloomLevel(rule.bloom_level.lower()))
            if rule.question_type:
                stmt = stmt.where(Question.type == QuestionType(rule.question_type.lower()))

            count_in_db = int((await self.db.execute(stmt)).scalar_one())
            gap = max(0, rule.count - count_in_db)
            matched = min(rule.count, count_in_db)

            total_avail += matched
            total_gap += gap

            availability_list.append({
                "rule_index": idx,
                "subject_id": rule.subject_id,
                "topic": rule.topic,
                "difficulty": rule.difficulty,
                "bloom_level": rule.bloom_level,
                "question_type": rule.question_type,
                "requested": rule.count,
                "available": count_in_db,
                "gap": gap,
            })

        return AvailabilityResult(
            total_requested=total_req,
            total_available=total_avail,
            total_gap=total_gap,
            rules_availability=availability_list,
        )

    async def fill_gaps_with_ai(
        self,
        rules: list[BlueprintRule],
        actor: User,
    ) -> list[Question]:
        """Generate missing questions for blueprint gaps using configured AI provider."""
        avail = await self.check_availability(rules)
        generated_questions: list[Question] = []
        provider = get_ai_provider()

        for item in avail.rules_availability:
            gap_count = item["gap"]
            if gap_count <= 0:
                continue

            rule_idx = item["rule_index"]
            rule = rules[rule_idx]

            prompt_text = f"Exam Blueprint Gap Filling for topic '{rule.topic or 'General'}'"
            ai_items = await provider.generate_questions(
                prompt=prompt_text,
                count=gap_count,
                difficulty=rule.difficulty,
                question_type=rule.question_type,
                topic=rule.topic,
                bloom_level=rule.bloom_level,
            )

            for ai_q in ai_items:
                try:
                    q_type = QuestionType(ai_q.type.lower())
                except ValueError:
                    q_type = QuestionType.MCQ

                try:
                    diff = Difficulty(ai_q.difficulty.lower())
                except ValueError:
                    diff = Difficulty.MEDIUM

                bloom = BloomLevel(ai_q.bloom_level.lower()) if ai_q.bloom_level else None

                question = Question(
                    type=q_type,
                    text=ai_q.text,
                    options=ai_q.options,
                    correct_answers=ai_q.correct_answers,
                    explanation=ai_q.explanation,
                    difficulty=diff,
                    bloom_level=bloom,
                    marks=rule.marks or ai_q.marks,
                    topic=rule.topic or ai_q.topic,
                    subject_id=rule.subject_id,
                    is_verified=True,
                    is_ai_generated=True,
                    created_by=actor.id,
                    version=1,
                )
                self.db.add(question)
                generated_questions.append(question)

        await self.db.flush()
        return generated_questions

    async def assemble_exam_from_blueprint(
        self,
        *,
        exam_id: str,
        rules: list[BlueprintRule],
    ) -> list[ExamQuestion]:
        """Assemble selected matching questions from Question Bank into ExamQuestion records."""
        result = await self.db.execute(select(Exam).where(Exam.id == exam_id, Exam.deleted_at.is_(None)))
        exam = result.scalar_one_or_none()
        if exam is None:
            raise NotFoundError("Exam not found")

        assembled_links: list[ExamQuestion] = []
        selected_question_ids: set[str] = set()
        display_order = 1

        for rule in rules:
            stmt = select(Question).where(Question.deleted_at.is_(None), Question.is_verified.is_(True))
            if rule.subject_id:
                stmt = stmt.where(Question.subject_id == rule.subject_id)
            if rule.topic:
                stmt = stmt.where(Question.topic.ilike(f"%{rule.topic}%"))
            if rule.difficulty:
                stmt = stmt.where(Question.difficulty == Difficulty(rule.difficulty.lower()))
            if rule.bloom_level:
                stmt = stmt.where(Question.bloom_level == BloomLevel(rule.bloom_level.lower()))
            if rule.question_type:
                stmt = stmt.where(Question.type == QuestionType(rule.question_type.lower()))

            if selected_question_ids:
                stmt = stmt.where(~Question.id.in_(selected_question_ids))

            matches = (await self.db.execute(stmt.limit(rule.count))).scalars().all()

            for q in matches:
                selected_question_ids.add(str(q.id))
                eq = ExamQuestion(
                    exam_id=exam.id,
                    question_id=q.id,
                    display_order=display_order,
                    marks=rule.marks or q.marks,
                )
                self.db.add(eq)
                assembled_links.append(eq)
                display_order += 1

        await self.db.flush()
        return assembled_links
