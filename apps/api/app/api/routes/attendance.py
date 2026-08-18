import csv
import hashlib
import hmac
import io
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import require_roles
from app.core.errors import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.db.models.academic import Department, Section, Semester
from app.db.models.attendance import AttendanceRecord, AttendanceSession, AttendanceStatus, SessionState
from app.db.models.question import Subject
from app.db.models.student import Student
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.pagination import PaginatedResponse
from app.services.audit import AuditService

router = APIRouter()


# ---------- Schemas ----------

class SessionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    subjectId: str | None = None
    departmentId: str | None = None
    semesterId: str | None = None
    sectionId: str | None = None
    sessionDate: str  # ISO string or YYYY-MM-DD
    startTime: str    # ISO string or HH:MM
    durationMinutes: int = Field(default=60, ge=5, le=480)


class ScanRequest(BaseModel):
    sessionId: str
    token: str


class RecordUpdate(BaseModel):
    status: AttendanceStatus
    notes: str | None = None


# ---------- Helpers ----------

async def _student_or_404(db: AsyncSession, user: User) -> Student:
    result = await db.execute(select(Student).where(Student.user_id == user.id))
    student = result.scalar_one_or_none()
    if student is None:
        student = Student(
            user_id=user.id,
            roll_number=f"STU-{str(user.id)[:8].upper()}",
        )
        db.add(student)
        await db.commit()
        await db.refresh(student)
    return student


def _generate_qr_token(secret: str, session_id: str, slot: int) -> str:
    msg = f"{session_id}:{slot}".encode()
    return hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()[:16]


async def _get_session_with_relations(db: AsyncSession, session_id: str) -> AttendanceSession | None:
    res = await db.execute(
        select(AttendanceSession)
        .options(
            selectinload(AttendanceSession.subject),
            selectinload(AttendanceSession.department),
            selectinload(AttendanceSession.semester),
            selectinload(AttendanceSession.section),
            selectinload(AttendanceSession.records),
        )
        .where(AttendanceSession.id == session_id, AttendanceSession.deleted_at.is_(None))
    )
    return res.scalar_one_or_none()


def _format_session(s: AttendanceSession) -> dict:
    end_time_dt = None
    if s.start_time:
        from datetime import timedelta
        end_time_dt = s.start_time + timedelta(minutes=s.duration_minutes)

    rec_list = getattr(s, "records", []) or []
    present_cnt = len([r for r in rec_list if getattr(r, "status", None) in (AttendanceStatus.PRESENT, "PRESENT", AttendanceStatus.LATE, "LATE")])
    absent_cnt = len([r for r in rec_list if getattr(r, "status", None) in (AttendanceStatus.ABSENT, "ABSENT")])
    total_cnt = present_cnt + absent_cnt
    pct = round((present_cnt / total_cnt * 100), 1) if total_cnt > 0 else 100.0

    return {
        "id": str(s.id),
        "title": s.title,
        "subject": {"id": str(s.subject.id), "name": s.subject.name, "code": s.subject.code} if getattr(s, "subject", None) else None,
        "department": {"id": str(s.department.id), "name": s.department.name} if getattr(s, "department", None) else None,
        "semester": {"id": str(s.semester.id), "name": s.semester.name} if getattr(s, "semester", None) else None,
        "section": {"id": str(s.section.id), "name": s.section.name} if getattr(s, "section", None) else None,
        "sessionDate": s.session_date.isoformat() if s.session_date else "",
        "startTime": s.start_time.isoformat() if s.start_time else "",
        "endTime": end_time_dt.isoformat() if end_time_dt else "",
        "durationMinutes": s.duration_minutes,
        "status": s.status.value if hasattr(s.status, "value") else str(s.status),
        "presentCount": present_cnt,
        "absentCount": absent_cnt,
        "percentage": pct,
        "createdAt": s.created_at.isoformat() if getattr(s, "created_at", None) else "",
    }


# ---------- Endpoints ----------

@router.post("/sessions", summary="Create attendance session draft")
async def create_session(
    body: SessionCreate,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    try:
        session_dt = datetime.fromisoformat(body.sessionDate.replace("Z", "+00:00"))
    except ValueError:
        session_dt = datetime.now(UTC)

    try:
        start_dt = datetime.fromisoformat(body.startTime.replace("Z", "+00:00"))
    except ValueError:
        start_dt = session_dt

    now_naive = datetime.now(UTC).replace(tzinfo=None)
    start_dt_naive = start_dt.replace(tzinfo=None) if start_dt.tzinfo else start_dt

    # If start time is current or in the past, activate immediately for QR scanning
    initial_status = SessionState.ACTIVE if start_dt_naive <= now_naive else SessionState.DRAFT

    session = AttendanceSession(
        title=body.title,
        subject_id=body.subjectId or None,
        department_id=body.departmentId or None,
        semester_id=body.semesterId or None,
        section_id=body.sectionId or None,
        created_by=actor.id,
        session_date=session_dt,
        start_time=start_dt,
        duration_minutes=body.durationMinutes,
        status=initial_status,
        qr_secret=secrets.token_hex(32),
    )
    db.add(session)
    await db.flush()

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="ATTENDANCE_SESSION_CREATED",
        entity_type="attendance_session",
        entity_id=str(session.id),
        new_value={"title": session.title, "status": initial_status.value},
    )
    await db.commit()

    full_session = await _get_session_with_relations(db, str(session.id))
    return _format_session(full_session or session)


@router.get("/sessions", summary="List attendance sessions")
async def list_sessions(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN, Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
    subject_id: str | None = None,
    department_id: str | None = None,
) -> PaginatedResponse[dict]:
    base = (
        select(AttendanceSession)
        .options(
            selectinload(AttendanceSession.subject),
            selectinload(AttendanceSession.department),
            selectinload(AttendanceSession.semester),
            selectinload(AttendanceSession.section),
            selectinload(AttendanceSession.records),
        )
        .where(AttendanceSession.deleted_at.is_(None))
        .order_by(AttendanceSession.created_at.desc())
    )

    if status_filter and status_filter != "all":
        try:
            base = base.where(AttendanceSession.status == SessionState(status_filter))
        except ValueError:
            pass

    if subject_id:
        base = base.where(AttendanceSession.subject_id == subject_id)
    if department_id:
        base = base.where(AttendanceSession.department_id == department_id)

    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    res = await db.execute(base.limit(page_size).offset((page - 1) * page_size))
    items = [_format_session(s) for s in res.scalars().all()]
    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(items=items, page=page, pageSize=page_size, total=total, totalPages=total_pages)


@router.get("/sessions/{session_id}", summary="Get attendance session details & counts")
async def get_session_detail(
    session_id: str,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN, Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    s = await _get_session_with_relations(db, session_id)
    if not s:
        raise NotFoundError("Attendance session not found")

    rec_res = await db.execute(
        select(AttendanceRecord.status, func.count(AttendanceRecord.id))
        .where(AttendanceRecord.session_id == session_id, AttendanceRecord.deleted_at.is_(None))
        .group_by(AttendanceRecord.status)
    )
    counts = dict(rec_res.all())
    present_cnt = counts.get(AttendanceStatus.PRESENT, 0)
    absent_cnt = counts.get(AttendanceStatus.ABSENT, 0)
    late_cnt = counts.get(AttendanceStatus.LATE, 0)

    out = _format_session(s)
    out["counts"] = {
        "present": present_cnt,
        "absent": absent_cnt,
        "late": late_cnt,
        "total": present_cnt + absent_cnt + late_cnt,
    }
    return out


@router.post("/sessions/{session_id}/activate", summary="Activate attendance session")
@router.post("/sessions/{session_id}/start", summary="Start attendance session")
async def activate_session(
    session_id: str,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    res = await db.execute(select(AttendanceSession).where(AttendanceSession.id == session_id))
    s = res.scalar_one_or_none()
    if not s:
        raise NotFoundError("Attendance session not found")

    s.status = SessionState.ACTIVE
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="ATTENDANCE_SESSION_ACTIVATED",
        entity_type="attendance_session",
        entity_id=session_id,
        new_value={"status": "ACTIVE"},
    )
    await db.commit()
    full_session = await _get_session_with_relations(db, session_id)
    return _format_session(full_session or s)


@router.post("/sessions/{session_id}/close", summary="Close attendance session and auto-mark ABSENT")
@router.post("/sessions/{session_id}/end", summary="End attendance session and auto-mark ABSENT")
async def close_session(
    session_id: str,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    res = await db.execute(select(AttendanceSession).where(AttendanceSession.id == session_id))
    s = res.scalar_one_or_none()
    if not s:
        raise NotFoundError("Attendance session not found")

    s.status = SessionState.CLOSED

    # Auto-mark unrecorded enrolled students as ABSENT
    st_stmt = select(Student).where(Student.deleted_at.is_(None))
    if s.department_id:
        st_stmt = st_stmt.where(Student.department_id == s.department_id)
    if s.semester_id:
        st_stmt = st_stmt.where(Student.semester_id == s.semester_id)
    if s.section_id:
        st_stmt = st_stmt.where(Student.section_id == s.section_id)

    st_res = await db.execute(st_stmt)
    students = st_res.scalars().all()

    existing_recs_res = await db.execute(
        select(AttendanceRecord.student_id).where(AttendanceRecord.session_id == session_id)
    )
    recorded_student_ids = {str(st_id) for st_id in existing_recs_res.scalars().all()}

    absent_count = 0
    now = datetime.now(UTC).replace(tzinfo=None)
    for st in students:
        if str(st.id) not in recorded_student_ids:
            rec = AttendanceRecord(
                session_id=s.id,
                student_id=st.id,
                status=AttendanceStatus.ABSENT,
                marked_at=now,
                verification_method="SYSTEM_AUTO_ABSENT",
                notes="Auto-marked absent on session closure",
            )
            db.add(rec)
            absent_count += 1

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="ATTENDANCE_SESSION_CLOSED",
        entity_type="attendance_session",
        entity_id=session_id,
        new_value={"status": "CLOSED", "auto_absent_count": absent_count},
    )
    await db.commit()
    return {"status": "CLOSED", "autoAbsentCount": absent_count}


@router.get("/qr/{session_id}", summary="Get dynamic QR token for active session")
@router.get("/sessions/{session_id}/qr", summary="Get dynamic QR token for active session")
async def get_dynamic_qr(
    session_id: str,
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    res = await db.execute(select(AttendanceSession).where(AttendanceSession.id == session_id))
    s = res.scalar_one_or_none()
    if not s:
        raise NotFoundError("Attendance session not found")
    if s.status != SessionState.ACTIVE:
        raise BadRequestError(f"Session is in {s.status.value} state. Only ACTIVE sessions generate QR codes.")

    ts = int(time.time())
    slot = ts // 30
    token = _generate_qr_token(s.qr_secret, str(s.id), slot)
    expires_in = 30 - (ts % 30)

    return {
        "sessionId": str(s.id),
        "title": s.title,
        "token": token,
        "expiresInSeconds": expires_in,
    }


@router.post("/scan", summary="Student scan QR token to mark attendance")
async def scan_qr_attendance(
    body: ScanRequest,
    user: Annotated[User, Depends(require_roles(Role.STUDENT, Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    student = await _student_or_404(db, user)

    res = await db.execute(select(AttendanceSession).where(AttendanceSession.id == body.sessionId))
    s = res.scalar_one_or_none()
    if not s:
        raise NotFoundError("Attendance session not found")
    if s.status != SessionState.ACTIVE:
        raise BadRequestError("This attendance session is not active")

    # Cohort / Batch Validation: Verify student belongs to session cohort
    if s.department_id and student.department_id and str(s.department_id) != str(student.department_id):
        raise ForbiddenError("You are not enrolled in the department assigned to this attendance session.")
    if s.semester_id and student.semester_id and str(s.semester_id) != str(student.semester_id):
        raise ForbiddenError("You are not enrolled in the semester assigned to this attendance session.")
    if s.section_id and student.section_id and str(s.section_id) != str(student.section_id):
        raise ForbiddenError("You are not enrolled in the section assigned to this attendance session.")

    # Validate HMAC token against current slot or previous slot (30-60s window)
    ts = int(time.time())
    current_slot = ts // 30
    prev_slot = current_slot - 1

    valid_token_1 = _generate_qr_token(s.qr_secret, str(s.id), current_slot)
    valid_token_2 = _generate_qr_token(s.qr_secret, str(s.id), prev_slot)

    if body.token not in (valid_token_1, valid_token_2):
        raise BadRequestError("Expired or invalid QR code. Ask your instructor for the latest QR code.")

    # Check for existing record
    dup_res = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == s.id,
            AttendanceRecord.student_id == student.id,
        )
    )
    if dup_res.scalar_one_or_none() is not None:
        raise ConflictError("Attendance has already been marked for this session.")

    now = datetime.now(UTC).replace(tzinfo=None)
    rec = AttendanceRecord(
        session_id=s.id,
        student_id=student.id,
        status=AttendanceStatus.PRESENT,
        marked_at=now,
        verification_method="QR_SCAN",
    )
    db.add(rec)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError("Attendance has already been recorded for this session.")

    return {
        "marked": True,
        "status": "PRESENT",
        "sessionTitle": s.title,
        "markedAt": now.isoformat(),
    }


@router.get("/records", summary="List attendance records (Admin table)")
async def list_records(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    session_id: str | None = None,
    subject_id: str | None = None,
    department_id: str | None = None,
    status_filter: str | None = None,
    date: str | None = None,
) -> PaginatedResponse[dict]:
    base = (
        select(AttendanceRecord)
        .join(Student, AttendanceRecord.student_id == Student.id)
        .outerjoin(User, Student.user_id == User.id)
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
        .options(
            selectinload(AttendanceRecord.student).selectinload(Student.user),
            selectinload(AttendanceRecord.student).selectinload(Student.department),
            selectinload(AttendanceRecord.student).selectinload(Student.semester),
            selectinload(AttendanceRecord.student).selectinload(Student.section),
            selectinload(AttendanceRecord.session).selectinload(AttendanceSession.subject),
        )
        .where(AttendanceRecord.deleted_at.is_(None))
        .order_by(AttendanceRecord.created_at.desc())
    )

    if session_id:
        base = base.where(AttendanceRecord.session_id == session_id)
    if status_filter and status_filter != "all":
        try:
            base = base.where(AttendanceRecord.status == AttendanceStatus(status_filter))
        except ValueError:
            pass
    if subject_id and subject_id != "all":
        base = base.where(AttendanceSession.subject_id == subject_id)
    if department_id and department_id != "all":
        base = base.where(Student.department_id == department_id)
    if date and date.strip():
        try:
            d_obj = datetime.fromisoformat(date.replace("Z", "+00:00")).date()
            base = base.where(func.date(AttendanceSession.session_date) == d_obj)
        except ValueError:
            pass
    if search:
        base = base.where(
            (Student.roll_number.ilike(f"%{search}%")) |
            (User.first_name.ilike(f"%{search}%")) |
            (User.last_name.ilike(f"%{search}%")) |
            (AttendanceSession.title.ilike(f"%{search}%"))
        )

    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())
    res = await db.execute(base.limit(page_size).offset((page - 1) * page_size))

    items = []
    for r in res.scalars().all():
        st = r.student
        sess = r.session
        batch_name = [
            st.department.name if (st and st.department) else None,
            st.semester.name if (st and st.semester) else None,
            st.section.name if (st and st.section) else None,
        ]
        clean_batch = " - ".join([b for b in batch_name if b]) or "General Cohort"

        items.append({
            "id": str(r.id),
            "studentId": str(st.id) if st else "",
            "studentRoll": st.roll_number if st else "",
            "studentName": st.full_name if st else "",
            "batch": clean_batch,
            "departmentName": st.department.name if (st and st.department) else "N/A",
            "subjectName": sess.subject.name if (sess and sess.subject) else (sess.title if sess else "N/A"),
            "sessionDate": sess.session_date.isoformat() if (sess and sess.session_date) else "",
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "verificationMethod": r.verification_method,
            "markedAt": r.marked_at.isoformat() if r.marked_at else "",
            "notes": r.notes,
        })

    total_pages = (total + page_size - 1) // page_size if total else 0
    return PaginatedResponse(items=items, page=page, pageSize=page_size, total=total, totalPages=total_pages)


@router.patch("/records/{record_id}", summary="Manual status override by Admin")
async def update_record_status(
    record_id: str,
    body: RecordUpdate,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    res = await db.execute(select(AttendanceRecord).where(AttendanceRecord.id == record_id))
    r = res.scalar_one_or_none()
    if not r:
        raise NotFoundError("Attendance record not found")

    old_status = r.status.value if hasattr(r.status, "value") else str(r.status)
    r.status = body.status
    r.verification_method = "MANUAL_ADMIN"
    if body.notes:
        r.notes = body.notes

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="ATTENDANCE_RECORD_UPDATED",
        entity_type="attendance_record",
        entity_id=record_id,
        old_value={"status": old_status},
        new_value={"status": body.status.value if hasattr(body.status, "value") else str(body.status)},
    )
    await db.commit()
    return {"id": record_id, "status": body.status.value if hasattr(body.status, "value") else str(body.status)}


@router.get("/students/me", summary="Student personal attendance summary & history")
async def student_my_attendance(
    user: Annotated[User, Depends(require_roles(Role.STUDENT, Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    student = await _student_or_404(db, user)

    recs_res = await db.execute(
        select(AttendanceRecord)
        .options(
            selectinload(AttendanceRecord.session).selectinload(AttendanceSession.subject)
        )
        .where(AttendanceRecord.student_id == student.id, AttendanceRecord.deleted_at.is_(None))
        .order_by(AttendanceRecord.created_at.desc())
    )
    records = recs_res.scalars().all()

    total_sessions = len(records)
    present_cnt = len([r for r in records if r.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE)])
    absent_cnt = len([r for r in records if r.status == AttendanceStatus.ABSENT])
    late_cnt = len([r for r in records if r.status == AttendanceStatus.LATE])

    pct = round((present_cnt / total_sessions * 100), 1) if total_sessions > 0 else 0.0

    # Subject breakdown
    subject_map: dict[str, dict] = {}
    for r in records:
        s_name = r.session.subject.name if (r.session and r.session.subject) else (r.session.title if r.session else "General")
        if s_name not in subject_map:
            subject_map[s_name] = {"subjectName": s_name, "total": 0, "present": 0, "absent": 0}
        subject_map[s_name]["total"] += 1
        if r.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE):
            subject_map[s_name]["present"] += 1
        else:
            subject_map[s_name]["absent"] += 1

    subject_breakdown = [
        {
            "subjectName": v["subjectName"],
            "total": v["total"],
            "present": v["present"],
            "absent": v["absent"],
            "percentage": round((v["present"] / v["total"] * 100), 1) if v["total"] > 0 else 0.0,
        }
        for v in subject_map.values()
    ]

    history = [
        {
            "id": str(r.id),
            "sessionTitle": r.session.title if r.session else "Session",
            "subjectName": r.session.subject.name if (r.session and r.session.subject) else "General",
            "sessionDate": r.session.session_date.isoformat() if (r.session and r.session.session_date) else "",
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "markedAt": r.marked_at.isoformat() if r.marked_at else "",
        }
        for r in records
    ]

    return {
        "overallPercentage": pct,
        "totalSessions": total_sessions,
        "presentCount": present_cnt,
        "absentCount": absent_cnt,
        "lateCount": late_cnt,
        "subjectBreakdown": subject_breakdown,
        "history": history,
    }


@router.get("/summary", summary="Attendance analytics overview & low-attendance list")
async def attendance_analytics_summary(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    low_threshold: float = Query(default=75.0, ge=0.0, le=100.0),
    department_id: str | None = None,
    date: str | None = None,
) -> dict:
    st_stmt = select(Student).options(selectinload(Student.user), selectinload(Student.department)).where(Student.deleted_at.is_(None))
    if department_id and department_id != "all":
        st_stmt = st_stmt.where(Student.department_id == department_id)

    st_res = await db.execute(st_stmt)
    students = st_res.scalars().all()

    total_students = len(students)
    student_stats = []

    grand_total_sessions = 0
    grand_present_sessions = 0
    grand_absent_sessions = 0

    for st in students:
        rec_stmt = select(AttendanceRecord).where(AttendanceRecord.student_id == st.id, AttendanceRecord.deleted_at.is_(None))
        if date and date.strip():
            try:
                d_obj = datetime.fromisoformat(date.replace("Z", "+00:00")).date()
                rec_stmt = rec_stmt.join(AttendanceSession).where(func.date(AttendanceSession.session_date) == d_obj)
            except ValueError:
                pass

        recs_res = await db.execute(rec_stmt)
        recs = recs_res.scalars().all()
        tot = len(recs)
        pres = len([r for r in recs if r.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE)])
        absent = len([r for r in recs if r.status == AttendanceStatus.ABSENT])
        pct = round((pres / tot * 100), 1) if tot > 0 else 0.0

        grand_total_sessions += tot
        grand_present_sessions += pres
        grand_absent_sessions += absent

        student_stats.append({
            "studentId": str(st.id),
            "rollNumber": st.roll_number,
            "name": st.full_name,
            "department": st.department.name if st.department else "N/A",
            "totalSessions": tot,
            "presentSessions": pres,
            "absentSessions": absent,
            "percentage": pct,
            "isLowAttendance": pct < low_threshold if tot > 0 else False,
        })

    overall_pct = round((grand_present_sessions / grand_total_sessions * 100), 1) if grand_total_sessions > 0 else 0.0
    low_attendance_students = [s for s in student_stats if s["isLowAttendance"]]

    # Recent sessions
    recent_sess_res = await db.execute(
        select(AttendanceSession)
        .options(
            selectinload(AttendanceSession.subject),
            selectinload(AttendanceSession.department),
            selectinload(AttendanceSession.semester),
            selectinload(AttendanceSession.section),
            selectinload(AttendanceSession.records),
        )
        .where(AttendanceSession.deleted_at.is_(None))
        .order_by(AttendanceSession.created_at.desc())
        .limit(5)
    )
    recent_sessions = [_format_session(s) for s in recent_sess_res.scalars().all()]

    return {
        "overallPercentage": overall_pct,
        "totalStudents": total_students,
        "totalPresentCount": grand_present_sessions,
        "totalAbsentCount": grand_absent_sessions,
        "lowAttendanceCount": len(low_attendance_students),
        "lowThreshold": low_threshold,
        "lowAttendanceStudents": low_attendance_students,
        "recentSessions": recent_sessions,
    }


@router.get("/export", summary="Export attendance records as CSV report")
async def export_attendance_csv(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    date: str | None = None,
    subject_id: str | None = None,
    department_id: str | None = None,
    status_filter: str | None = None,
) -> StreamingResponse:
    base = (
        select(AttendanceRecord)
        .join(Student, AttendanceRecord.student_id == Student.id)
        .outerjoin(User, Student.user_id == User.id)
        .join(AttendanceSession, AttendanceRecord.session_id == AttendanceSession.id)
        .options(
            selectinload(AttendanceRecord.student).selectinload(Student.user),
            selectinload(AttendanceRecord.student).selectinload(Student.department),
            selectinload(AttendanceRecord.student).selectinload(Student.semester),
            selectinload(AttendanceRecord.student).selectinload(Student.section),
            selectinload(AttendanceRecord.session).selectinload(AttendanceSession.subject),
        )
        .where(AttendanceRecord.deleted_at.is_(None))
        .order_by(AttendanceRecord.created_at.desc())
    )

    if status_filter and status_filter != "all":
        try:
            base = base.where(AttendanceRecord.status == AttendanceStatus(status_filter))
        except ValueError:
            pass
    if subject_id and subject_id != "all":
        base = base.where(AttendanceSession.subject_id == subject_id)
    if department_id and department_id != "all":
        base = base.where(Student.department_id == department_id)
    if date and date.strip():
        try:
            d_obj = datetime.fromisoformat(date.replace("Z", "+00:00")).date()
            base = base.where(func.date(AttendanceSession.session_date) == d_obj)
        except ValueError:
            pass

    res = await db.execute(base)
    records = res.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Student Name", "Roll Number", "Batch", "Subject", "Date",
        "Session Start", "Session End", "Status", "Check-in Time", "Attendance Percentage"
    ])

    dept_name = "ALL"
    for r in records:
        st = r.student
        sess = r.session
        batch_parts = [
            st.department.name if (st and st.department) else None,
            st.semester.name if (st and st.semester) else None,
            st.section.name if (st and st.section) else None,
        ]
        clean_batch = " - ".join([b for b in batch_parts if b]) or "General Batch"
        if st and st.department:
            dept_name = st.department.name.replace(" ", "_")

        s_date = sess.session_date.strftime("%Y-%m-%d") if (sess and sess.session_date) else ""
        s_start = sess.start_time.strftime("%H:%M") if (sess and sess.start_time) else ""
        s_end = (sess.start_time + timedelta(minutes=sess.duration_minutes)).strftime("%H:%M") if (sess and sess.start_time and sess.duration_minutes) else ""
        c_time = r.marked_at.strftime("%H:%M:%S") if r.marked_at else "-"
        pct_str = "100%" if r.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE) else "0%"

        writer.writerow([
            st.full_name if st else "",
            st.roll_number if st else "",
            clean_batch,
            sess.subject.name if (sess and sess.subject) else (sess.title if sess else "N/A"),
            s_date,
            s_start,
            s_end,
            r.status.value if hasattr(r.status, "value") else str(r.status),
            c_time,
            pct_str,
        ])

    output.seek(0)
    file_date = date or datetime.now(UTC).strftime("%Y-%m-%d")
    filename = f"attendance_{dept_name}_{file_date}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
