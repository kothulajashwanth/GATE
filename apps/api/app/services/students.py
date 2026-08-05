from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.db.models.student import Student
from app.db.models.user import User
from app.repositories.student import StudentRepository


class StudentService:
    """Business rules for student management."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = StudentRepository(db)

    async def list(
        self,
        *,
        query: str | None = None,
        department_id: Any | None = None,
        semester_id: Any | None = None,
        section_id: Any | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        return await self.repo.search(
            query=query,
            department_id=department_id,
            semester_id=semester_id,
            section_id=section_id,
            is_active=is_active,
            page=page,
            page_size=page_size,
        )

    async def get_profile(self, user: User) -> Student:
        """Student profile for the current user."""
        student = await self.repo.get_by_user_id(user.id)
        if student is None:
            raise NotFoundError("Student profile not found")
        return student
