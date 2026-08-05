"""Development seed data. Idempotent: safe to re-run.

Usage:
    python -m app.db.seed
"""

import asyncio

from sqlalchemy import select

import app.db.base  # noqa: F401  (imports all models so string relationships resolve)
from app.db.models.academic import Department, Section, Semester
from app.db.models.question import (
    BloomLevel,
    Difficulty,
    Question,
    QuestionBankFolder,
    QuestionType,
    Subject,
)
from app.db.models.user import Role, User
from app.db.session import AsyncSessionLocal


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        # --- Users ---
        result = await db.execute(select(User).where(User.email == "kothulajashwanth@gmail.com"))
        admin = result.scalar_one_or_none()
        if admin is None:
            admin = User(
                email="kothulajashwanth@gmail.com",
                first_name="Admin",
                last_name="User",
                role=Role.ADMIN,
                is_active=True,
            )
            db.add(admin)
            await db.flush()

        # --- Academic ---
        result = await db.execute(select(Department).where(Department.code == "CSE"))
        dept = result.scalar_one_or_none()
        if dept is None:
            dept = Department(name="Computer Science & Engineering", code="CSE", description="CSE department")
            db.add(dept)
            await db.flush()

        result = await db.execute(select(Semester).where(Semester.department_id == dept.id, Semester.ordinal == 3))
        sem = result.scalar_one_or_none()
        if sem is None:
            sem = Semester(department_id=dept.id, name="Semester III", ordinal=3, academic_year="2025-26")
            db.add(sem)
            await db.flush()

        result = await db.execute(select(Section).where(Section.department_id == dept.id, Section.semester_id == sem.id, Section.code == "A"))
        section = result.scalar_one_or_none()
        if section is None:
            section = Section(department_id=dept.id, semester_id=sem.id, name="Section A", code="A")
            db.add(section)
            await db.flush()

        # --- Question bank ---
        result = await db.execute(select(Subject).where(Subject.code == "DSA"))
        subject = result.scalar_one_or_none()
        if subject is None:
            subject = Subject(name="Data Structures & Algorithms", code="DSA", department_id=dept.id)
            db.add(subject)
            await db.flush()

        result = await db.execute(select(QuestionBankFolder).where(QuestionBankFolder.name == "DSA Core"))
        folder = result.scalar_one_or_none()
        if folder is None:
            folder = QuestionBankFolder(name="DSA Core", created_by=admin.id)
            db.add(folder)
            await db.flush()

        result = await db.execute(select(Question).where(Question.text.ilike("%Big-O%"), Question.subject_id == subject.id))
        if result.scalar_one_or_none() is None:
            questions = [
                Question(
                    folder_id=folder.id,
                    subject_id=subject.id,
                    created_by=admin.id,
                    type=QuestionType.MCQ,
                    text="What is the time complexity of accessing an element in an array by index?",
                    options=["O(1)", "O(log n)", "O(n)", "O(n log n)"],
                    correct_answers=["O(1)"],
                    explanation="Array indexing is direct memory access, constant time.",
                    difficulty=Difficulty.EASY,
                    bloom_level=BloomLevel.REMEMBER,
                    tags=["arrays", "complexity"],
                    marks=1,
                    is_verified=True,
                ),
                Question(
                    folder_id=folder.id,
                    subject_id=subject.id,
                    created_by=admin.id,
                    type=QuestionType.TRUE_FALSE,
                    text="A binary search tree allows duplicates on the left subtree.",
                    options=["True", "False"],
                    correct_answers=["False"],
                    explanation="BST ordering varies by convention, but standard BSTs store unique keys.",
                    difficulty=Difficulty.MEDIUM,
                    bloom_level=BloomLevel.UNDERSTAND,
                    tags=["trees", "bst"],
                    marks=1,
                    is_verified=True,
                ),
                Question(
                    folder_id=folder.id,
                    subject_id=subject.id,
                    created_by=admin.id,
                    type=QuestionType.MCQ,
                    text="Which data structure is best for implementing a FIFO queue?",
                    options=["Stack", "Linked List", "Binary Heap", "Hash Map"],
                    correct_answers=["Linked List"],
                    explanation="A linked list supports O(1) enqueue and dequeue operations.",
                    difficulty=Difficulty.EASY,
                    bloom_level=BloomLevel.REMEMBER,
                    tags=["queue", "linked-list"],
                    marks=1,
                    is_verified=True,
                ),
                Question(
                    folder_id=folder.id,
                    subject_id=subject.id,
                    created_by=admin.id,
                    type=QuestionType.FILL_BLANK,
                    text="The worst-case time complexity of quicksort is ____.",
                    options=None,
                    correct_answers=["O(n^2)", "O(n2)"],
                    explanation="When pivots are poorly chosen, quicksort degrades to quadratic time.",
                    difficulty=Difficulty.MEDIUM,
                    bloom_level=BloomLevel.UNDERSTAND,
                    tags=["sorting", "quicksort"],
                    marks=2,
                    is_verified=True,
                ),
            ]
            db.add_all(questions)

        await db.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())
