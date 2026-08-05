from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ValidationError
from app.db.models.academic import Department, Section, Semester
from app.db.models.student import Student
from app.db.models.user import Role, User
from app.repositories.student import StudentRepository

# Column order expected in the import template.
EXPECTED_HEADERS = [
    "roll_number", "first_name", "last_name", "email", "phone",
    "department_code", "semester_ordinal", "section_code",
    "parent_name", "parent_phone",
]


@dataclass
class ImportResult:
    total: int = 0
    imported: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def failed(self) -> int:
        return len(self.errors)


def _row_error(row_number: int, message: str) -> dict[str, Any]:
    return {"row": row_number, "error": message}


async def import_students_from_excel(db: AsyncSession, file: BytesIO) -> ImportResult:
    """Parse, validate and insert students from an Excel workbook.

    Validation happens before any insert; on any error the whole import is
    rolled back (single transaction). A per-row error list is returned for
    the admin error report.
    """
    from openpyxl import load_workbook

    result = ImportResult()
    try:
        wb = load_workbook(file, read_only=True, data_only=True)
    except Exception:
        raise ValidationError("Could not parse the Excel file. Use the provided template.")

    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    try:
        header = [str(c).strip().lower() if c else "" for c in next(rows)]
    except StopIteration:
        raise ValidationError("The Excel file is empty")

    if header != EXPECTED_HEADERS:
        raise ValidationError(
            f"Invalid headers. Expected: {', '.join(EXPECTED_HEADERS)}. Got: {', '.join(header)}"
        )

    # Preload reference maps for validation (department code -> id, etc.)
    dept_map: dict[str, str] = {}
    for row in (await db.execute(select(Department))).scalars().all():
        dept_map[row.code] = str(row.id)
    sem_map: dict[tuple[str, int], str] = {}
    for row in (await db.execute(select(Semester))).scalars().all():
        sem_map[(str(row.department_id), row.ordinal)] = str(row.id)
    sec_map: dict[tuple[str, str], str] = {}
    for row in (await db.execute(select(Section))).scalars().all():
        sec_map[(str(row.semester_id), row.code)] = str(row.id)

    existing_rolls = {
        r[0] for r in (await db.execute(select(Student.roll_number))).all()
    }
    existing_emails = {r[0] for r in (await db.execute(select(User.email))).all()}

    parsed: list[dict[str, Any]] = []
    row_number = 1  # header consumed
    for raw in rows:
        row_number += 1
        if raw is None or all(c is None or str(c).strip() == "" for c in raw):
            continue
        result.total += 1

        def cell(idx: int) -> str:
            v = raw[idx] if idx < len(raw) else None
            return str(v).strip() if v is not None else ""

        roll = cell(0)
        email = cell(3).lower()
        dept_code = cell(5).upper()
        sem_ord = cell(6)
        sec_code = cell(7).upper()

        # --- validate row ---
        errors: list[str] = []
        if not roll:
            errors.append("Roll number is required")
        elif roll in existing_rolls or any(p["roll_number"] == roll for p in parsed):
            errors.append(f"Duplicate roll number '{roll}'")
        if not email:
            errors.append("Email is required")
        elif email in existing_emails or any(p["email"] == email for p in parsed):
            errors.append(f"Duplicate email '{email}'")
        elif "@" not in email:
            errors.append(f"Invalid email '{email}'")
        if not dept_code or dept_code not in dept_map:
            errors.append(f"Unknown department code '{dept_code}'")
        if sem_ord not in (1, 2, 3, 4, 5, 6, 7, 8):
            errors.append(f"Invalid semester ordinal '{sem_ord}' (1-8)")
        dept_id = dept_map.get(dept_code)
        sem_id = sem_map.get((dept_id, int(sem_ord))) if dept_id and sem_ord in (1, 2, 3, 4, 5, 6, 7, 8) else None
        if dept_id and sem_ord in (1, 2, 3, 4, 5, 6, 7, 8) and not sem_id:
            errors.append(f"Semester {sem_ord} not found for department '{dept_code}'")
        sec_id = sec_map.get((sem_id, sec_code)) if sem_id else None
        if dept_id and sem_id and not sec_code:
            errors.append("Section code is required")
        elif sem_id and sec_code and not sec_id:
            errors.append(f"Section '{sec_code}' not found in semester {sem_ord}")

        if errors:
            result.errors.append(_row_error(row_number, "; ".join(errors)))
            continue

        parsed.append({
            "roll_number": roll,
            "first_name": cell(1),
            "last_name": cell(2),
            "email": email,
            "phone": cell(4) or None,
            "department_id": dept_id,
            "semester_id": sem_id,
            "section_id": sec_id,
            "parent_name": cell(8) or None,
            "parent_phone": cell(9) or None,
        })

    if result.errors:
        # Abort entirely; the UI shows the error report.
        return result

    # --- insert (same transaction; rollback on any failure) ---
    try:
        for p in parsed:
            user = User(
                email=p["email"],
                first_name=p["first_name"],
                last_name=p["last_name"] or None,
                phone=p["phone"],
                role=Role.STUDENT,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            student = Student(
                user_id=user.id,
                roll_number=p["roll_number"],
                department_id=p["department_id"],
                semester_id=p["semester_id"],
                section_id=p["section_id"],
                phone=p["phone"],
                parent_name=p["parent_name"],
                parent_phone=p["parent_phone"],
            )
            db.add(student)
        await db.flush()
    except Exception:
        await db.rollback()
        raise ValidationError("Import failed mid-insert. All rows rolled back.")
    await db.commit()
    result.imported = len(parsed)
    return result