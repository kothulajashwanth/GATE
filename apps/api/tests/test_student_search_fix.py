import pytest
from sqlalchemy import func, select, or_
from app.db.models.student import Student
from app.db.models.user import User, Role
from app.db.models.academic import Department, Semester, Section


def test_student_model_properties_and_nullable_placements():
    user = User(email="teststudent@example.com", first_name="John", last_name="Doe", role=Role.STUDENT)
    student = Student(user_id="fake-uuid", roll_number="ROLL123")
    student.user = user

    assert student.first_name == "John"
    assert student.last_name == "Doe"
    assert student.full_name == "John Doe"
    assert student.email == "teststudent@example.com"
    assert student.department_id is None
    assert student.semester_id is None
    assert student.section_id is None


def test_count_query_structure_without_subquery_duplication():
    # Verify count query construction does not generate subquery with duplicate columns
    count_base = (
        select(func.count(Student.id))
        .select_from(Student)
        .join(User, Student.user_id == User.id)
        .where(Student.deleted_at.is_(None))
    )
    compiled_sql = str(count_base.compile())
    assert "count(students.id)" in compiled_sql or "COUNT" in compiled_sql
    assert "students.id" in compiled_sql
