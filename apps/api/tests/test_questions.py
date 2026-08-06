"""Unit tests for Question Document Parser (Phase 5)."""

import pytest
from app.services.document_parser import parse_text_content, parse_document


def test_parse_text_content_questions():
    sample_text = """Q1. What is Python?
A) Programming Language
B) Snake species
C) Database
D) Operating system
Answer: A
Difficulty: EASY
"""
    questions = parse_text_content(sample_text)
    assert len(questions) == 1
    assert questions[0]["title"] == "What is Python?"
    assert questions[0]["answer"] == "A"
    assert len(questions[0]["options"]) == 4


def test_parse_document_fallback():
    parsed = parse_document(b"Sample question text file", "sample.txt")
    assert len(parsed) >= 1
