import json
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError, ValidationError
from app.db.models.academic import Topic
from app.db.models.question import (
    BloomLevel,
    Difficulty,
    FailedQuestion,
    Question,
    QuestionOption,
    QuestionType,
    QuestionVersion,
    Subject,
    UploadedFile,
)
from app.db.models.user import User


class QuestionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_files(self) -> list[UploadedFile]:
        """List all uploaded question repository files."""
        result = await self.db.execute(
            select(UploadedFile).order_by(UploadedFile.created_at.desc()).limit(100)
        )
        return list(result.scalars().all())

    async def get_file(self, file_id: str) -> UploadedFile:
        result = await self.db.execute(select(UploadedFile).where(UploadedFile.id == file_id))
        f = result.scalar_one_or_none()
        if f is None:
            raise NotFoundError("Uploaded file not found")
        return f

    async def create_uploaded_file(
        self,
        *,
        file_name: str,
        original_name: str,
        file_type: str,
        file_size: int,
        storage_url: str,
        uploaded_by: Any,
    ) -> UploadedFile:
        uf = UploadedFile(
            file_name=file_name,
            original_name=original_name,
            file_type=file_type,
            file_size=file_size,
            storage_url=storage_url,
            uploaded_by=uploaded_by,
            status="UPLOADED",
            questions_found=0,
            ocr_used=False,
        )
        self.db.add(uf)
        await self.db.flush()
        return uf

    async def confirm_import(
        self,
        *,
        file_id: str,
        actor: User,
        questions_data: list[dict[str, Any]],
        subject_id: str | None = None,
        folder_id: str | None = None,
        auto_approve: bool = False,
    ) -> list[Question]:
        """Insert confirmed questions, options, and initial QuestionVersion snapshots."""
        uploaded_file = await self.get_file(file_id)

        created_questions: list[Question] = []

        for q_dict in questions_data:
            q_text = q_dict.get("text") or q_dict.get("title") or ""
            if not q_text.strip():
                continue

            q_type_str = q_dict.get("type") or q_dict.get("question_type") or "mcq"
            try:
                q_type = QuestionType(q_type_str.lower())
            except ValueError:
                q_type = QuestionType.MCQ

            diff_str = q_dict.get("difficulty") or "medium"
            try:
                diff = Difficulty(diff_str.lower())
            except ValueError:
                diff = Difficulty.MEDIUM

            options_list = q_dict.get("options") or []
            correct_ans_list = q_dict.get("correct_answers") or q_dict.get("correctAnswers") or [q_dict.get("answer", "A")]
            marks = int(q_dict.get("marks") or 1)
            neg_marks = float(q_dict.get("negative_marks") or q_dict.get("negativeMarks") or 0.0)
            explanation = q_dict.get("explanation")
            topic_str = q_dict.get("topic") or q_dict.get("topic_name")
            target_subject_id = q_dict.get("subject_id") or q_dict.get("subjectId") or subject_id
            is_verified = bool(q_dict.get("is_verified", auto_approve))

            question = Question(
                type=q_type,
                text=q_text,
                options=options_list,
                correct_answers=correct_ans_list,
                explanation=explanation,
                difficulty=diff,
                marks=marks,
                negative_marks=neg_marks,
                topic=topic_str,
                subject_id=target_subject_id,
                folder_id=folder_id,
                source_file_id=uploaded_file.id,
                created_by=actor.id,
                is_verified=is_verified,
                version=1,
            )
            self.db.add(question)
            await self.db.flush()

            # Create QuestionOption records for MCQs and multi-select
            if options_list and isinstance(options_list, list):
                for idx, opt_text in enumerate(options_list):
                    opt_letter = chr(65 + idx)  # A, B, C, D...
                    is_correct = opt_letter in correct_ans_list or str(idx) in correct_ans_list or opt_text in correct_ans_list
                    q_opt = QuestionOption(
                        question_id=question.id,
                        option_text=str(opt_text),
                        is_correct=is_correct,
                        display_order=idx + 1,
                    )
                    self.db.add(q_opt)

            # Create initial QuestionVersion snapshot
            version_snapshot = {
                "id": str(question.id),
                "version": 1,
                "text": question.text,
                "type": question.type.value,
                "options": options_list,
                "correct_answers": correct_ans_list,
                "difficulty": question.difficulty.value,
                "marks": question.marks,
                "explanation": question.explanation,
                "created_at": datetime.now(UTC).isoformat(),
            }
            qv = QuestionVersion(
                question_id=question.id,
                version=1,
                snapshot=version_snapshot,
                change_summary="Initial import from source file",
                changed_by=actor.id,
            )
            self.db.add(qv)
            created_questions.append(question)

        uploaded_file.status = "COMPLETED"
        uploaded_file.questions_found = len(created_questions)
        await self.db.flush()
        return created_questions

    async def create_question_version(
        self,
        question: Question,
        actor: User,
        change_summary: str = "Updated question profile",
    ) -> QuestionVersion:
        """Create new immutable snapshot in question_versions."""
        new_version_num = question.version + 1
        question.version = new_version_num

        snapshot = {
            "id": str(question.id),
            "version": new_version_num,
            "text": question.text,
            "type": question.type.value,
            "options": question.options,
            "correct_answers": question.correct_answers,
            "difficulty": question.difficulty.value,
            "marks": question.marks,
            "negative_marks": question.negative_marks,
            "explanation": question.explanation,
            "topic": question.topic,
            "subject_id": str(question.subject_id) if question.subject_id else None,
            "is_verified": question.is_verified,
            "updated_at": datetime.now(UTC).isoformat(),
        }

        qv = QuestionVersion(
            question_id=question.id,
            version=new_version_num,
            snapshot=snapshot,
            change_summary=change_summary,
            changed_by=actor.id,
        )
        self.db.add(qv)
        await self.db.flush()
        return qv

    async def approve_questions(self, question_ids: list[str], actor: User) -> int:
        """Mark list of questions as APPROVED (is_verified = True)."""
        result = await self.db.execute(
            select(Question).where(Question.id.in_(question_ids), Question.deleted_at.is_(None))
        )
        questions = result.scalars().all()
        approved_count = 0
        for q in questions:
            if not q.is_verified:
                q.is_verified = True
                approved_count += 1
                await self.create_question_version(q, actor, change_summary="Approved question for examinations")
        await self.db.flush()
        return approved_count

