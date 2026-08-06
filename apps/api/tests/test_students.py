"""Unit and integration tests for Student Management module (Phase 4)."""

import pytest
from app.db.models.student import Student
from app.db.models.user import Role, User


def test_student_roll_number_formatting():
    roll = "  cs2024001  "
    assert roll.strip().upper() == "CS2024001"


def test_student_role_verification():
    user = User(email="student@college.edu", first_name="Test", role=Role.STUDENT, is_active=True)
    assert user.role == Role.STUDENT
    assert user.is_active is True
