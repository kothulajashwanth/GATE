"""Unit tests for Exam Builder & Exam Engine modules (Phases 8 & 9)."""

import pytest
from app.db.models.exam import Exam, ExamStatus


def test_exam_duration_and_negative_marks():
    exam = Exam(
        title="Mid-term Data Structures",
        duration_minutes=60,
        total_marks=100,
        passing_marks=40,
        negative_marks_value=0.25,
        status=ExamStatus.PUBLISHED,
    )
    assert exam.duration_minutes == 60
    assert exam.negative_marks_value == 0.25
    assert exam.status == ExamStatus.PUBLISHED
