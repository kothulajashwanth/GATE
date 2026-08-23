from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.db.models.attendance import AttendanceStatus, SessionState


class AttendanceSessionCreate(BaseModel):
    title: Optional[str] = None
    subject_id: str
    department_id: Optional[str] = None
    semester_id: Optional[str] = None
    section_id: Optional[str] = None
    date: Optional[date] = None
    start_time: Optional[str] = "09:00"
    duration_minutes: Optional[int] = 60
    status: Optional[SessionState] = SessionState.ACTIVE


class AttendanceSessionResponse(BaseModel):
    id: str
    title: str
    subject_id: str
    subject_name: str
    department_id: Optional[str] = None
    department_name: Optional[str] = None
    semester_id: Optional[str] = None
    semester_name: Optional[str] = None
    section_id: Optional[str] = None
    section_name: Optional[str] = None
    date: date
    start_time: str
    duration_minutes: int
    status: SessionState
    created_at: datetime
    total_students: int = 0
    present_count: int = 0
    absent_count: int = 0
    pending_count: int = 0
    attendance_percentage: float = 0.0


class StudentAttendanceItem(BaseModel):
    id: Optional[str] = None
    student_id: str
    name: str
    roll_number: str
    batch: str
    status: str
    marked_at: Optional[datetime] = None


class SessionDetailResponse(BaseModel):
    session: AttendanceSessionResponse
    records: list[StudentAttendanceItem]


class AttendanceSubmitRequest(BaseModel):
    session_id: str
    status: AttendanceStatus = AttendanceStatus.PRESENT
    remarks: Optional[str] = None


class AttendanceRecordResponse(BaseModel):
    id: str
    session_id: str
    student_id: str
    status: AttendanceStatus
    marked_at: datetime


class StudentActiveSessionResponse(BaseModel):
    id: str
    title: str
    subject_id: str
    subject_name: str
    date: date
    start_time: str
    duration_minutes: int
    status: SessionState
    already_submitted: bool = False
    submitted_status: Optional[str] = None


class SubjectAttendancePercentage(BaseModel):
    subject_id: str
    subject_name: str
    total_sessions: int
    present_count: int
    absent_count: int
    percentage: float


class StudentAttendanceHistoryResponse(BaseModel):
    total_sessions: int
    present_count: int
    absent_count: int
    overall_percentage: float
    subject_stats: list[SubjectAttendancePercentage]
    records: list[dict]
