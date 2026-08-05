"""Result calculation service.

Evaluates exam sessions:
- Auto-evaluation for objective questions (MCQ, True/False, Fill Blank, Multi-Select)
- Manual evaluation flag for subjective questions (Paragraph, Coding)
- Score aggregation, percentage, pass/fail, rank computation
"""

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.exam import Exam, ExamQuestion
from app.db.models.question import Question, QuestionType
from app.db.models.result import ExamResult, ResultStatus
from app.db.models.session import ExamSession, SessionAnswer, SessionStatus


class ResultCalculator:
    """Core result computation logic."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def evaluate_session(self, session: ExamSession) -> ExamResult:
        """Compute and persist result for a completed session."""
        exam = await self._get_exam(session.exam_id)
        questions = await self._get_exam_questions(exam.id)
        answers = await self._get_session_answers(session.id)

        total_marks = sum(q.marks for q in questions)
        obtained_marks = 0.0
        question_analysis = []

        for q in questions:
            ans = answers.get(str(q.id))
            q_result = await self._evaluate_question(q, ans)
            obtained_marks += q_result.marks_awarded
            question_analysis.append(q_result.to_dict())

        percentage = (obtained_marks / total_marks * 100) if total_marks > 0 else 0
        is_passed = percentage >= exam.passing_marks if exam.passing_marks > 0 else None

        result = ExamResult(
            session_id=session.id,
            exam_id=exam.id,
            student_id=session.student_id,
            total_marks=total_marks,
            obtained_marks=obtained_marks,
            percentage=round(percentage, 2),
            is_passed=is_passed,
            evaluated_by="auto",
            status=ResultStatus.AUTO,
            question_analysis=question_analysis,
        )
        self.db.add(result)
        await self.db.flush()
        return result

    async def _get_exam(self, exam_id: Any) -> Exam:
        result = await self.db.execute(select(Exam).where(Exam.id == exam_id))
        return result.scalar_one()

    async def _get_exam_questions(self, exam_id: Any) -> list[Question]:
        result = await self.db.execute(
            select(ExamQuestion, Question)
            .join(Question, ExamQuestion.question_id == Question.id)
            .where(ExamQuestion.exam_id == exam_id)
            .order_by(ExamQuestion.order_index)
        )
        return [row.Question for row in result.all()]

    async def _get_session_answers(self, session_id: Any) -> dict[str, SessionAnswer]:
        result = await self.db.execute(
            select(SessionAnswer).where(SessionAnswer.session_id == session_id)
        )
        return {str(a.question_id): a for a in result.scalars().all()}

    async def _evaluate_question(self, question: Question, answer: SessionAnswer | None) -> "QuestionResult":
        """Evaluate a single question based on its type (delegates to pure scorer)."""
        result = QuestionResult.evaluate(question, answer)
        result.question_id = str(question.id)
        return result

    async def compute_ranks(self, exam_id: Any) -> None:
        """Compute rank for all published results of an exam."""
        results = await self.db.execute(
            select(ExamResult)
            .where(ExamResult.exam_id == exam_id, ExamResult.status != ResultStatus.PENDING)
            .order_by(ExamResult.obtained_marks.desc())
        )
        ranked = list(results.scalars().all())
        for rank, r in enumerate(ranked, start=1):
            r.rank = rank

    async def publish_results(self, exam_id: Any) -> None:
        """Mark all AUTO results as PUBLISHED."""
        result = await self.db.execute(
            select(ExamResult).where(ExamResult.exam_id == exam_id, ExamResult.status == ResultStatus.AUTO)
        )
        for r in result.scalars().all():
            r.status = ResultStatus.PUBLISHED
            from datetime import datetime, UTC
            r.published_at = datetime.now(UTC)

    async def get_student_results(self, student_id: Any) -> list[ExamResult]:
        result = await self.db.execute(
            select(ExamResult)
            .where(ExamResult.student_id == student_id)
            .order_by(ExamResult.created_at.desc())
        )
        return list(result.scalars().all())


class QuestionResult:
    """Single question evaluation result."""

    def __init__(
        self,
        question_id: str,
        is_answered: bool,
        is_correct: bool | None,
        marks_awarded: float,
        max_marks: int,
        negative_marks: float,
        time_taken: int | None,
    ) -> None:
        self.question_id = question_id
        self.is_answered = is_answered
        self.is_correct = is_correct
        self.marks_awarded = marks_awarded
        self.max_marks = max_marks
        self.negative_marks = negative_marks
        self.time_taken = time_taken

    def to_dict(self) -> dict:
        return {
            "questionId": self.question_id,
            "isAnswered": self.is_answered,
            "isCorrect": self.is_correct,
            "marksAwarded": self.marks_awarded,
            "maxMarks": self.max_marks,
            "negativeMarks": self.negative_marks,
            "timeTaken": self.time_taken,
        }

    @staticmethod
    def evaluate(question, answer) -> "QuestionResult":
        """Pure scoring logic (no DB). Extracted for unit testing.

        `question` exposes: .type (QuestionType), .correct_answers, .marks, .negative_marks.
        `answer` exposes: .answer (list) or None, .time_taken_seconds.
        """
        from app.db.models.question import QuestionType as QT

        time_taken = answer.time_taken_seconds if answer else None

        if answer is None or not answer.answer:
            return QuestionResult(
                question_id="",
                is_answered=False,
                is_correct=False,
                marks_awarded=0.0,
                max_marks=question.marks,
                negative_marks=0.0,
                time_taken=time_taken,
            )

        is_correct = False
        marks_awarded = 0.0
        negative = 0.0

        if question.type in (QT.MCQ, QT.TRUE_FALSE, QT.MULTI_SELECT):
            if set(answer.answer) == set(question.correct_answers):
                is_correct = True
                marks_awarded = question.marks
            else:
                negative = question.negative_marks

        elif question.type == QT.FILL_BLANK:
            user_ans = str(answer.answer[0]).strip().lower()
            correct_lower = [str(c).strip().lower() for c in question.correct_answers]
            if user_ans in correct_lower:
                is_correct = True
                marks_awarded = question.marks
            else:
                negative = question.negative_marks

        elif question.type in (QT.PARAGRAPH, QT.CODING):
            is_correct = None
            marks_awarded = None
            negative = 0.0

        return QuestionResult(
            question_id="",
            is_answered=True,
            is_correct=is_correct,
            marks_awarded=marks_awarded if marks_awarded is not None else 0.0,
            max_marks=question.marks,
            negative_marks=negative,
            time_taken=time_taken,
        )