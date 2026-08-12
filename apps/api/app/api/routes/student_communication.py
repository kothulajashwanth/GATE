from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import require_roles
from app.db.models.user import Role, User
from app.db.models.student import Student
from app.db.models.student_communication import StudentQuery, Feedback
from app.db.session import get_db
from app.core.errors import NotFoundError

router = APIRouter()


class StudentQueryCreate(BaseModel):
    exam_id: UUID | None = None
    query_text: str


class FeedbackCreate(BaseModel):
    exam_id: UUID | None = None
    feedback_text: str
    anonymous: bool = False


async def _student_or_404(db: AsyncSession, user_id) -> Student:
    result = await db.execute(select(Student).where(Student.user_id == user_id))
    student = result.scalar_one_or_none()
    if student is None:
        raise NotFoundError("Student profile not found. Contact administration.")
    return student


@router.post("/queries", status_code=status.HTTP_201_CREATED, summary="Submit a student query")
async def submit_query(
    query_data: StudentQueryCreate,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    student = await _student_or_404(db, user.id)
    new_query = StudentQuery(
        student_id=student.id,
        exam_id=query_data.exam_id,
        query_text=query_data.query_text,
    )
    db.add(new_query)
    await db.commit()
    await db.refresh(new_query)
    return {"message": "Query submitted successfully", "query_id": new_query.id}


@router.post("/feedback", status_code=status.HTTP_201_CREATED, summary="Submit student feedback")
async def submit_feedback(
    feedback_data: FeedbackCreate,
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    student = await _student_or_404(db, user.id)

    # If feedback is anonymous, do not link student_id
    student_id_to_store = student.id if not feedback_data.anonymous else None

    new_feedback = Feedback(
        student_id=student_id_to_store,
        exam_id=feedback_data.exam_id,
        feedback_text=feedback_data.feedback_text,
        anonymous=feedback_data.anonymous,
    )
    db.add(new_feedback)
    await db.commit()
    await db.refresh(new_feedback)
    return {"message": "Feedback submitted successfully", "feedback_id": new_feedback.id}
