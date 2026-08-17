from typing import Any

from sqlalchemy import func, or_, select

from app.core.errors import ConflictError
from app.db.models.academic import Department, Section, Semester
from app.db.models.student import Student
from app.db.models.user import Role, User
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository[Student]):
    model = Student

    async def get_by_roll_number(self, roll_number: str) -> Student | None:
        stmt = self._live_filter(select(Student).where(Student.roll_number == roll_number))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id) -> Student | None:
        stmt = self._live_filter(select(Student).where(Student.user_id == user_id))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
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
        """Search students with filters, joining academic placements.

        Returns (rows, total). Rows are dicts shaped for the API response.
        """
        import uuid

        def _clean_uuid(val: Any) -> uuid.UUID | None:
            if not val or not isinstance(val, str) or val.strip() in ("", "all", "none", "null", "undefined"):
                return None
            try:
                return uuid.UUID(val.strip())
            except ValueError:
                return None

        dept_uuid = _clean_uuid(department_id)
        sem_uuid = _clean_uuid(semester_id)
        sec_uuid = _clean_uuid(section_id)

        base = (
            select(Student, User, Department, Semester, Section)
            .join(User, Student.user_id == User.id)
            .outerjoin(Department, Student.department_id == Department.id)
            .outerjoin(Semester, Student.semester_id == Semester.id)
            .outerjoin(Section, Student.section_id == Section.id)
            .where(Student.deleted_at.is_(None), User.deleted_at.is_(None))
        )

        if query and query.strip():
            like = f"%{query.strip()}%"
            base = base.where(
                or_(
                    Student.roll_number.ilike(like),
                    User.first_name.ilike(like),
                    User.last_name.ilike(like),
                    User.email.ilike(like),
                )
            )
        if dept_uuid:
            base = base.where(Student.department_id == dept_uuid)
        if sem_uuid:
            base = base.where(Student.semester_id == sem_uuid)
        if sec_uuid:
            base = base.where(Student.section_id == sec_uuid)
        if is_active is not None:
            base = base.where(User.is_active == is_active)

        count_base = (
            select(func.count(Student.id))
            .select_from(Student)
            .join(User, Student.user_id == User.id)
            .where(Student.deleted_at.is_(None), User.deleted_at.is_(None))
        )
        if query and query.strip():
            like = f"%{query.strip()}%"
            count_base = count_base.where(
                or_(
                    Student.roll_number.ilike(like),
                    User.first_name.ilike(like),
                    User.last_name.ilike(like),
                    User.email.ilike(like),
                )
            )
        if dept_uuid:
            count_base = count_base.where(Student.department_id == dept_uuid)
        if sem_uuid:
            count_base = count_base.where(Student.semester_id == sem_uuid)
        if sec_uuid:
            count_base = count_base.where(Student.section_id == sec_uuid)
        if is_active is not None:
            count_base = count_base.where(User.is_active == is_active)

        total = int((await self.db.execute(count_base)).scalar_one())

        rows_result = await self.db.execute(
            base.order_by(User.first_name).limit(page_size).offset((page - 1) * page_size)
        )
        rows = [
            {
                "id": str(student.id),
                "rollNumber": student.roll_number or f"STU-{str(student.id)[:8].upper()}",
                "name": user.full_name if user else (student.roll_number or "Student"),
                "email": user.email if user else "",
                "phone": student.phone,
                "isActive": bool(user.is_active) if user else True,
                "department": {"id": str(dept.id), "name": dept.name} if (dept and dept.id and dept.name) else None,
                "semester": {"id": str(sem.id), "name": sem.name} if (sem and sem.id and sem.name) else None,
                "section": {"id": str(sec.id), "name": sec.name} if (sec and sec.id and sec.name) else None,
            }
            for student, user, dept, sem, sec in rows_result.all()
        ]
        return rows, total

    async def create_student(
        self,
        *,
        user: User,
        roll_number: str,
        department_id,
        semester_id,
        section_id,
        phone: str | None = None,
        parent_name: str | None = None,
        parent_phone: str | None = None,
        enrollment_year: int | None = None,
    ) -> Student:
        if await self.get_by_roll_number(roll_number):
            raise ConflictError(f"Roll number '{roll_number}' already exists")
        user.role = Role.STUDENT
        return await self.create(
            user_id=user.id,
            roll_number=roll_number,
            department_id=department_id,
            semester_id=semester_id,
            section_id=section_id,
            phone=phone,
            parent_name=parent_name,
            parent_phone=parent_phone,
            enrollment_year=enrollment_year,
        )
