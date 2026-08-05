from sqlalchemy import select

from app.core.errors import ConflictError
from app.db.models.academic import Department, Section, Semester
from app.repositories.base import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    model = Department

    async def get_by_code(self, code: str) -> Department | None:
        result = await self.db.execute(
            self._live_filter(select(Department).where(Department.code == code))
        )
        return result.scalar_one_or_none()

    async def create_with_check(self, *, name: str, code: str, description: str | None = None) -> Department:
        if await self.get_by_code(code):
            raise ConflictError(f"Department code '{code}' already exists")
        return await self.create(name=name, code=code, description=description)


class SemesterRepository(BaseRepository[Semester]):
    model = Semester

    async def list_by_department(self, department_id) -> list[Semester]:
        result = await self.db.execute(
            self._live_filter(
                select(Semester)
                .where(Semester.department_id == department_id)
                .order_by(Semester.ordinal)
            )
        )
        return list(result.scalars().all())


class SectionRepository(BaseRepository[Section]):
    model = Section

    async def list_by_department(self, department_id) -> list[Section]:
        result = await self.db.execute(
            self._live_filter(
                select(Section).where(Section.department_id == department_id).order_by(Section.name)
            )
        )
        return list(result.scalars().all())

    async def list_by_semester(self, semester_id) -> list[Section]:
        result = await self.db.execute(
            self._live_filter(
                select(Section).where(Section.semester_id == semester_id).order_by(Section.name)
            )
        )
        return list(result.scalars().all())
