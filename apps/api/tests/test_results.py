import pytest

from app.services.results import QuestionResult


class FakeAnswer:
    def __init__(self, answer, time_taken=30):
        self.answer = answer
        self.time_taken_seconds = time_taken


class FakeQuestion:
    def __init__(self, qtype, correct_answers, marks=2, negative_marks=0.5, id="q1"):
        self.type = qtype
        self.correct_answers = correct_answers
        self.marks = marks
        self.negative_marks = negative_marks
        self.id = id


def test_mcq_correct():
    q = FakeQuestion("mcq", ["A"])
    r = QuestionResult.evaluate(q, FakeAnswer(["A"]))
    assert r.is_correct is True
    assert r.marks_awarded == 2
    assert r.negative_marks == 0


def test_mcq_wrong_gets_negative():
    q = FakeQuestion("mcq", ["A"])
    r = QuestionResult.evaluate(q, FakeAnswer(["B"]))
    assert r.is_correct is False
    assert r.negative_marks == 0.5


def test_fill_blank_case_insensitive():
    q = FakeQuestion("fill_blank", ["O(n^2)", "O(n2)"])
    r = QuestionResult.evaluate(q, FakeAnswer(["o(n^2)"]))
    assert r.is_correct is True


def test_multi_select_exact_match():
    q = FakeQuestion("multi_select", ["A", "C"])
    r = QuestionResult.evaluate(q, FakeAnswer(["A", "C"]))
    assert r.is_correct is True
    r2 = QuestionResult.evaluate(q, FakeAnswer(["A"]))
    assert r2.is_correct is False


def test_unanswered_is_zero():
    q = FakeQuestion("mcq", ["A"])
    r = QuestionResult.evaluate(q, None)
    assert r.is_answered is False
    assert r.marks_awarded == 0


def test_subjective_flags_manual():
    q = FakeQuestion("paragraph", [])
    r = QuestionResult.evaluate(q, FakeAnswer(["essay"]))
    assert r.is_correct is None
