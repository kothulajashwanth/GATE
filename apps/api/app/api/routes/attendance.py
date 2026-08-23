import csv
from datetime import date, datetime, timezone, timedelta
from io import StringIO
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user, require_roles
from app.core.errors import BadRequestError, ForbiddenError, NotFoundError
from app.db.models.academic import Department, Section, Semester
from app.db.models.attendance import AttendanceRecord, AttendanceSession, AttendanceStatus, SessionState
from app.db.models.question import Subject
from app.db.models.student import Student
from app.db.models.user import Role, User
from app.db.session import get_db
from app.schemas.attendance import (
    AttendanceRecordResponse,
    AttendanceSessionCreate,
    AttendanceSessionResponse,
    AttendanceSubmitRequest,
    SessionDetailResponse,
    StudentActiveSessionResponse,
    StudentAttendanceHistoryResponse,
    StudentAttendanceItem,
    SubjectAttendancePercentage,
)

router = APIRouter()


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
    return res.scalars().first()


def _format_session_stats(s: AttendanceSession, total_batch_students: int) -> dict:
    records = s.records or []
    present_cnt = len([r for r in records if r.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE)])
    absent_cnt = len([r for r in records if r.status == AttendanceStatus.ABSENT])
    total_cnt = max(total_batch_students, present_cnt + absent_cnt)
    pending_cnt = max(0, total_cnt - (present_cnt + absent_cnt))
    pct = round((present_cnt / total_cnt * 100), 1) if total_cnt > 0 else 0.0

    dept_name = s.department.name if s.department else "All Depts"
    sem_name = s.semester.name if s.semester else "All Semesters"
    sec_name = s.section.name if s.section else "All Sections"

    return {
        "id": str(s.id),
        "title": s.title,
        "subject_id": str(s.subject_id),
        "subject_name": s.subject.name if s.subject else "Unknown Subject",
        "department_id": str(s.department_id) if s.department_id else None,
        "department_name": dept_name,
        "semester_id": str(s.semester_id) if s.semester_id else None,
        "semester_name": sem_name,
        "section_id": str(s.section_id) if s.section_id else None,
        "section_name": sec_name,
        "date": s.date,
        "start_time": s.start_time,
        "duration_minutes": s.duration_minutes,
        "status": s.status,
        "created_at": s.created_at,
        "total_students": total_cnt,
        "present_count": present_cnt,
        "absent_count": absent_cnt,
        "pending_count": pending_cnt,
        "attendance_percentage": pct,
    }


@router.post("/sessions", response_model=AttendanceSessionResponse, summary="Create attendance session")
async def create_session(
    payload: AttendanceSessionCreate,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    subj_res = await db.execute(select(Subject).where(Subject.id == payload.subject_id))
    subject = subj_res.scalars().first()
    if not subject:
        raise NotFoundError("Subject not found")

    title = payload.title
    if not title:
        title = f"{subject.name} Attendance"

    session = AttendanceSession(
        title=title,
        subject_id=payload.subject_id,
        department_id=payload.department_id,
        semester_id=payload.semester_id,
        section_id=payload.section_id,
        date=payload.date or date.today(),
        start_time=payload.start_time or "09:00",
        duration_minutes=payload.duration_minutes or 60,
        status=payload.status or SessionState.ACTIVE,
        created_by=str(actor.id),
    )
    db.add(session)
    await db.commit()

    full_session = await _get_session_with_relations(db, str(session.id))
    
    # Calculate batch students count
    stu_q = select(func.count(Student.id)).where(Student.deleted_at.is_(None))
    if session.department_id:
        stu_q = stu_q.where(Student.department_id == session.department_id)
    if session.semester_id:
        stu_q = stu_q.where(Student.semester_id == session.semester_id)
    if session.section_id:
        stu_q = stu_q.where(Student.section_id == session.section_id)
    
    cnt_res = await db.execute(stu_q)
    total_batch_students = cnt_res.scalar() or 0

    return _format_session_stats(full_session, total_batch_students)


@router.get("/sessions", response_model=list[AttendanceSessionResponse], summary="List attendance sessions")
async def list_sessions(
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Optional[str] = Query(None, alias="status"),
    subject_id: Optional[str] = Query(None),
    department_id: Optional[str] = Query(None),
) -> list[dict]:
    q = (
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

    if status_filter and status_filter.upper() in SessionState.__members__:
        q = q.where(AttendanceSession.status == SessionState(status_filter.upper()))
    if subject_id:
        q = q.where(AttendanceSession.subject_id == subject_id)
    if department_id:
        q = q.where(AttendanceSession.department_id == department_id)

    res = await db.execute(q)
    sessions = res.scalars().all()

    out = []
    for s in sessions:
        stu_q = select(func.count(Student.id)).where(Student.deleted_at.is_(None))
        if s.department_id:
            stu_q = stu_q.where(Student.department_id == s.department_id)
        if s.semester_id:
            stu_q = stu_q.where(Student.semester_id == s.semester_id)
        if s.section_id:
            stu_q = stu_q.where(Student.section_id == s.section_id)
        cnt_res = await db.execute(stu_q)
        batch_cnt = cnt_res.scalar() or 0
        out.append(_format_session_stats(s, batch_cnt))

    return out


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse, summary="Get session details and student roster")
async def get_session_detail(
    session_id: str,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    session = await _get_session_with_relations(db, session_id)
    if not session:
        raise NotFoundError("Attendance session not found")

    # Fetch all students belonging to the session batch
    stu_q = (
        select(Student)
        .options(
            selectinload(Student.user),
            selectinload(Student.department),
            selectinload(Student.semester),
            selectinload(Student.section),
        )
        .where(Student.deleted_at.is_(None))
    )
    if session.department_id:
        stu_q = stu_q.where(Student.department_id == session.department_id)
    if session.semester_id:
        stu_q = stu_q.where(Student.semester_id == session.semester_id)
    if session.section_id:
        stu_q = stu_q.where(Student.section_id == session.section_id)

    stu_res = await db.execute(stu_q)
    students = stu_res.scalars().all()

    record_map = {r.student_id: r for r in (session.records or [])}

    roster_items = []
    for st in students:
        rec = record_map.get(str(st.id))
        dept_code = st.department.name if st.department else ""
        sem_code = st.semester.name if st.semester else ""
        sec_code = st.section.name if st.section else ""
        batch_str = " - ".join(filter(None, [dept_code, sem_code, sec_code])) or "General"

        name = st.user.full_name if st.user else st.roll_number
        st_status = rec.status.value if rec else "PENDING"
        marked_at = rec.marked_at if rec else None

        roster_items.append(
            StudentAttendanceItem(
                id=str(rec.id) if rec else None,
                student_id=str(st.id),
                name=name,
                roll_number=st.roll_number,
                batch=batch_str,
                status=st_status,
                marked_at=marked_at,
            )
        )

    stats = _format_session_stats(session, len(students))
    return {
        "session": stats,
        "records": roster_items,
    }


@router.post("/sessions/{session_id}/close", summary="Close attendance session")
async def close_session(
    session_id: str,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    session = await _get_session_with_relations(db, session_id)
    if not session:
        raise NotFoundError("Attendance session not found")

    session.status = SessionState.CLOSED

    # Auto-mark unsubmitted batch students as ABSENT
    stu_q = select(Student).where(Student.deleted_at.is_(None))
    if session.department_id:
        stu_q = stu_q.where(Student.department_id == session.department_id)
    if session.semester_id:
        stu_q = stu_q.where(Student.semester_id == session.semester_id)
    if session.section_id:
        stu_q = stu_q.where(Student.section_id == session.section_id)

    stu_res = await db.execute(stu_q)
    students = stu_res.scalars().all()

    existing_student_ids = {r.student_id for r in (session.records or [])}
    for st in students:
        st_id = str(st.id)
        if st_id not in existing_student_ids:
            rec = AttendanceRecord(
                session_id=str(session.id),
                student_id=st_id,
                status=AttendanceStatus.ABSENT,
                remarks="Auto-marked ABSENT on session closure",
            )
            db.add(rec)

    await db.commit()
    session = await _get_session_with_relations(db, session_id)
    return _format_session_stats(session, len(students))


@router.get("/sessions/{session_id}/export", summary="Export attendance CSV")
async def export_session_csv(
    session_id: str,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    session = await _get_session_with_relations(db, session_id)
    if not session:
        raise NotFoundError("Attendance session not found")

    detail = await get_session_detail(session_id, actor, db)
    roster = detail["records"]

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Roll Number", "Student Name", "Batch", "Status", "Marked At"])

    for item in roster:
        marked_str = item.marked_at.strftime("%Y-%m-%d %H:%M:%S") if item.marked_at else "-"
        writer.writerow([item.roll_number, item.name, item.batch, item.status, marked_str])

    output.seek(0)
    filename = f"attendance_{session.subject.name if session.subject else 'session'}_{session.date}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/student/active", response_model=Optional[StudentActiveSessionResponse], summary="Get active session for student's batch")
async def get_student_active_session(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Optional[dict]:
    stu_res = await db.execute(select(Student).where(Student.user_id == user.id, Student.deleted_at.is_(None)))
    student = stu_res.scalars().first()
    if not student:
        return None

    # Search for active session matching student's department/semester/section
    q = (
        select(AttendanceSession)
        .options(selectinload(AttendanceSession.subject))
        .where(AttendanceSession.status == SessionState.ACTIVE, AttendanceSession.deleted_at.is_(None))
        .order_by(AttendanceSession.created_at.desc())
    )
    if student.department_id:
        q = q.where(
            (AttendanceSession.department_id.is_(None)) | (AttendanceSession.department_id == student.department_id)
        )
    if student.semester_id:
        q = q.where(
            (AttendanceSession.semester_id.is_(None)) | (AttendanceSession.semester_id == student.semester_id)
        )
    if student.section_id:
        q = q.where(
            (AttendanceSession.section_id.is_(None)) | (AttendanceSession.section_id == student.section_id)
        )

    res = await db.execute(q)
    sessions = res.scalars().all()
    if not sessions:
        return None

    for sess in sessions:
        # Check if student already submitted attendance for this session
        rec_res = await db.execute(
            select(AttendanceRecord).where(
                AttendanceRecord.session_id == str(sess.id),
                AttendanceRecord.student_id == str(student.id),
                AttendanceRecord.deleted_at.is_(None),
            )
        )
        existing_rec = rec_res.scalars().first()

        already_submitted = existing_rec is not None
        submitted_status = existing_rec.status.value if existing_rec else None

        if not already_submitted:
            return {
                "id": str(sess.id),
                "title": sess.title,
                "subject_id": str(sess.subject_id),
                "subject_name": sess.subject.name if sess.subject else "Subject",
                "date": sess.date,
                "start_time": sess.start_time,
                "duration_minutes": sess.duration_minutes,
                "status": sess.status,
                "already_submitted": False,
                "submitted_status": None,
            }

    return None


@router.post("/student/submit", response_model=AttendanceRecordResponse, summary="Submit student attendance (PRESENT or ABSENT)")
async def submit_student_attendance(
    payload: AttendanceSubmitRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    stu_res = await db.execute(select(Student).where(Student.user_id == user.id, Student.deleted_at.is_(None)))
    student = stu_res.scalars().first()
    if not student:
        raise ForbiddenError("Student profile not found for current user")

    sess_res = await db.execute(
        select(AttendanceSession).where(
            AttendanceSession.id == payload.session_id, AttendanceSession.deleted_at.is_(None)
        )
    )
    sess = sess_res.scalars().first()
    if not sess:
        raise NotFoundError("Attendance session not found")

    if sess.status != SessionState.ACTIVE:
        raise BadRequestError("This attendance session is no longer active")

    # Verify student belongs to session batch
    if sess.department_id and student.department_id and sess.department_id != student.department_id:
        raise ForbiddenError("You are not enrolled in the batch for this session")
    if sess.semester_id and student.semester_id and sess.semester_id != student.semester_id:
        raise ForbiddenError("You are not enrolled in the semester for this session")

    # Check for duplicate submission
    dup_res = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == payload.session_id,
            AttendanceRecord.student_id == str(student.id),
            AttendanceRecord.deleted_at.is_(None),
        )
    )
    if dup_res.scalars().first():
        raise BadRequestError("Attendance already submitted for this session")

    record = AttendanceRecord(
        session_id=payload.session_id,
        student_id=str(student.id),
        status=payload.status,
        remarks=payload.remarks or "Submitted by student",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {
        "id": str(record.id),
        "session_id": str(record.session_id),
        "student_id": str(record.student_id),
        "status": record.status,
        "marked_at": record.marked_at,
    }


@router.get("/student/records", response_model=StudentAttendanceHistoryResponse, summary="Get student attendance history & percentages")
async def get_student_attendance_history(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    stu_res = await db.execute(select(Student).where(Student.user_id == user.id, Student.deleted_at.is_(None)))
    student = stu_res.scalars().first()
    if not student:
        return {
            "total_sessions": 0,
            "present_count": 0,
            "absent_count": 0,
            "overall_percentage": 0.0,
            "subject_stats": [],
            "records": [],
        }

    # Fetch all records for this student
    rec_res = await db.execute(
        select(AttendanceRecord)
        .options(
            selectinload(AttendanceRecord.session).selectinload(AttendanceSession.subject)
        )
        .where(AttendanceRecord.student_id == str(student.id), AttendanceRecord.deleted_at.is_(None))
        .order_by(AttendanceRecord.marked_at.desc())
    )
    records = rec_res.scalars().all()

    total_sessions = len(records)
    present_cnt = len([r for r in records if r.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE)])
    absent_cnt = len([r for r in records if r.status == AttendanceStatus.ABSENT])
    overall_pct = round((present_cnt / total_sessions * 100), 1) if total_sessions > 0 else 0.0

    # Group by subject
    subj_map: dict[str, dict] = {}
    formatted_records = []
    for r in records:
        sess = r.session
        subj = sess.subject if sess else None
        subj_id = str(subj.id) if subj else "unknown"
        subj_name = subj.name if subj else "Unknown Subject"

        if subj_id not in subj_map:
            subj_map[subj_id] = {
                "subject_id": subj_id,
                "subject_name": subj_name,
                "total_sessions": 0,
                "present_count": 0,
                "absent_count": 0,
            }
        subj_map[subj_id]["total_sessions"] += 1
        if r.status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE):
            subj_map[subj_id]["present_count"] += 1
        else:
            subj_map[subj_id]["absent_count"] += 1

        formatted_records.append({
            "id": str(r.id),
            "session_id": str(r.session_id),
            "subject_name": subj_name,
            "date": str(sess.date) if sess else str(r.marked_at.date()),
            "status": r.status.value,
            "marked_at": r.marked_at.isoformat(),
        })

    subject_stats = []
    for item in subj_map.values():
        tot = item["total_sessions"]
        pres = item["present_count"]
        pct = round((pres / tot * 100), 1) if tot > 0 else 0.0
        subject_stats.append(
            SubjectAttendancePercentage(
                subject_id=item["subject_id"],
                subject_name=item["subject_name"],
                total_sessions=tot,
                present_count=pres,
                absent_count=item["absent_count"],
                percentage=pct,
            )
        )

    return {
        "total_sessions": total_sessions,
        "present_count": present_cnt,
        "absent_count": absent_cnt,
        "overall_percentage": overall_pct,
        "subject_stats": subject_stats,
        "records": formatted_records,
    }
