from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StudentSessionData(BaseModel):
    user_id: UUID
    login_time: datetime
    status: str = "logged_in"  # Initial status
    exam_id: UUID | None = None # Will be set when student starts an exam
    last_activity: datetime


class AdminActiveStudent(BaseModel):
    user_id: UUID
    email: str
    full_name: str
    login_time: datetime
    status: str
    exam_id: UUID | None
    last_activity: datetime
