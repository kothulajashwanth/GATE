#!/usr/bin/env python3
"""
Bulk Student Import Script for ExamShield AI.
Supports both standard template and registration form Excel formats (e.g. Google Forms).

Usage:
    python scripts/import_students.py "C:\\path\\to\\file.xlsx"
    python scripts/import_students.py "C:\\path\\to\\file.xlsx" --db-url "postgresql+asyncpg://..."
"""

import sys
import os
import io
import re
import asyncio
from pathlib import Path

# Add apps/api to Python path
ROOT_DIR = Path(__file__).resolve().parent.parent
API_DIR = ROOT_DIR / "apps" / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

# Ensure environment variables are loaded
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")
load_dotenv(API_DIR / ".env")

import openpyxl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

import app.db.base  # noqa: F401
from app.db.models.academic import Department, Section, Semester
from app.db.models.student import Student
from app.db.models.user import Role, User


def parse_year_to_semester(year_str: str) -> int:
    """Map 'IV Year', '4th Year', 'III Year', '3rd Year' to semester ordinal (1-8)."""
    s = str(year_str).upper()
    if "IV" in s or "4" in s:
        return 7
    elif "III" in s or "3" in s:
        return 5
    elif "II" in s or "2" in s:
        return 3
    elif "I" in s or "1" in s:
        return 1
    return 5


def parse_section(sec_str: str) -> tuple[str, str]:
    """Parse 'CSM B', 'CSE A', 'B' -> (dept_code, section_code)."""
    s = str(sec_str).strip()
    parts = s.split()
    if len(parts) == 2:
        return parts[0].upper(), parts[1].upper()
    elif len(parts) == 1:
        return "CSE", parts[0].upper()
    return "CSE", "A"


async def ensure_academic_hierarchy(db: AsyncSession, dept_code: str, sem_ord: int, sec_code: str):
    """Ensure Department, Semester, and Section exist in database, creating if missing."""
    # 1. Department
    res = await db.execute(select(Department).where(Department.code == dept_code))
    dept = res.scalar_one_or_none()
    if not dept:
        dept = Department(
            name=f"Department of {dept_code}",
            code=dept_code,
            description=f"Auto-created {dept_code} department",
        )
        db.add(dept)
        await db.flush()

    # 2. Semester
    res = await db.execute(
        select(Semester).where(Semester.department_id == dept.id, Semester.ordinal == sem_ord)
    )
    sem = res.scalar_one_or_none()
    if not sem:
        sem = Semester(
            department_id=dept.id,
            name=f"Semester {sem_ord}",
            ordinal=sem_ord,
            academic_year="2026-27",
        )
        db.add(sem)
        await db.flush()

    # 3. Section
    res = await db.execute(
        select(Section).where(
            Section.department_id == dept.id,
            Section.semester_id == sem.id,
            Section.code == sec_code,
        )
    )
    sec = res.scalar_one_or_none()
    if not sec:
        sec = Section(
            department_id=dept.id,
            semester_id=sem.id,
            name=f"Section {sec_code}",
            code=sec_code,
        )
        db.add(sec)
        await db.flush()

    return dept, sem, sec


async def import_custom_excel(file_path: str, db_url: str):
    path = Path(file_path)
    if not path.is_file():
        print(f"Error: File not found: '{file_path}'")
        sys.exit(1)

    print(f"Opening Excel workbook: {path.name}...")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        print("Error: Excel sheet is empty!")
        sys.exit(1)

    header_raw = [str(c).strip() if c else "" for c in rows[0]]
    header_lower = [h.lower() for h in header_raw]

    print("\nDetected Excel Columns:")
    print(" | ".join(header_raw))

    def get_col_index(keywords: list[str]) -> int | None:
        for idx, h in enumerate(header_lower):
            if any(k in h for k in keywords):
                return idx
        return None

    col_name = get_col_index(["full name", "name", "first_name"])
    col_roll = get_col_index(["roll number", "roll_number", "roll", "registration number"])
    col_email = get_col_index(["college email id", "college email", "email", "personal email id"])
    col_phone = get_col_index(["mobile number", "mobile", "phone"])
    col_year = get_col_index(["year of study", "year", "semester"])
    col_section = get_col_index(["section"])

    if col_roll is None or col_name is None:
        print("Error: Could not identify 'Roll Number' or 'Full Name' columns!")
        sys.exit(1)

    engine = create_async_engine(db_url, pool_pre_ping=True)
    SessionMaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print(f"\nConnecting to PostgreSQL Database...")

    try:
        async with SessionMaker() as db:
            existing_rolls_res = await db.execute(select(Student.roll_number))
            existing_rolls = {r[0].strip().upper() for r in existing_rolls_res.all() if r[0]}

            existing_emails_res = await db.execute(select(User.email))
            existing_emails = {r[0].strip().lower() for r in existing_emails_res.all() if r[0]}

            total_rows = 0
            added_count = 0
            skipped_count = 0
            errors = []

            for row_idx, row in enumerate(rows[1:], start=2):
                if not row or all(c is None or str(c).strip() == "" for c in row):
                    continue

                total_rows += 1

                raw_roll = str(row[col_roll]).strip() if col_roll is not None and row[col_roll] is not None else ""
                raw_name = str(row[col_name]).strip() if col_name is not None and row[col_name] is not None else ""
                raw_email = str(row[col_email]).strip().lower() if col_email is not None and row[col_email] is not None else ""
                raw_phone = str(row[col_phone]).strip() if col_phone is not None and row[col_phone] is not None else ""
                raw_year = str(row[col_year]).strip() if col_year is not None and row[col_year] is not None else "III Year"
                raw_sec = str(row[col_section]).strip() if col_section is not None and row[col_section] is not None else "A"

                if not raw_roll or not raw_name:
                    skipped_count += 1
                    continue

                roll_clean = raw_roll.upper()
                if not raw_email:
                    raw_email = f"{roll_clean.lower()}@college.edu"

                if roll_clean in existing_rolls or raw_email in existing_emails:
                    skipped_count += 1
                    continue

                name_parts = raw_name.split(maxsplit=1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""

                if raw_phone.endswith(".0"):
                    raw_phone = raw_phone[:-2]

                sem_ord = parse_year_to_semester(raw_year)
                dept_code, sec_code = parse_section(raw_sec)

                try:
                    dept, sem, sec = await ensure_academic_hierarchy(db, dept_code, sem_ord, sec_code)

                    user = User(
                        email=raw_email,
                        first_name=first_name,
                        last_name=last_name or None,
                        phone=raw_phone or None,
                        role=Role.STUDENT,
                        is_active=True,
                    )
                    db.add(user)
                    await db.flush()

                    student = Student(
                        user_id=user.id,
                        roll_number=roll_clean,
                        department_id=dept.id,
                        semester_id=sem.id,
                        section_id=sec.id,
                        phone=raw_phone or None,
                    )
                    db.add(student)
                    await db.flush()

                    existing_rolls.add(roll_clean)
                    existing_emails.add(raw_email)
                    added_count += 1

                except Exception as e:
                    errors.append(f"Row {row_idx} ({raw_name} - {roll_clean}): {str(e)}")

            await db.commit()

            print("\n" + "=" * 55)
            print("          STUDENT REGISTRATION IMPORT SUMMARY         ")
            print("=" * 55)
            print(f" Total Rows Processed : {total_rows}")
            print(f" Students Successfully Added : {added_count}")
            print(f" Skipped (Duplicates/Empty): {skipped_count}")

            if errors:
                print(f"\n Errors ({len(errors)}):")
                for err in errors[:10]:
                    print(f"  - {err}")
    except Exception as e:
        print(f"\nDatabase Connection Error: {e}")
        print("\nNote: Make sure your PostgreSQL database is running, or provide your Render DATABASE_URL:")
        print('python scripts/import_students.py "path/to/file.xlsx" --db-url "postgresql+asyncpg://user:pass@host:5432/dbname"')
    finally:
        await engine.dispose()


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/import_students.py <excel_file_path> [--db-url <connection_string>]")
        sys.exit(1)
    
    file_path = sys.argv[1]
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://examshield:examshield_dev@localhost:5432/examshield")

    if "--db-url" in sys.argv:
        idx = sys.argv.index("--db-url")
        if idx + 1 < len(sys.argv):
            db_url = sys.argv[idx + 1]

    asyncio.run(import_custom_excel(file_path, db_url))


if __name__ == "__main__":
    main()
