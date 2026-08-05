from pydantic import BaseModel, EmailStr, Field


class StudentRow(BaseModel):
    id: str
    rollNumber: str
    name: str
    email: str
    phone: str | None = None
    isActive: bool
    department: dict[str, str] | None = None
    semester: dict[str, str] | None = None
    section: dict[str, str] | None = None


class StudentCreate(BaseModel):
    rollNumber: str = Field(min_length=1, max_length=40)
    email: EmailStr
    firstName: str = Field(min_length=1, max_length=120)
    lastName: str | None = None
    phone: str | None = Field(default=None, max_length=30)
    departmentId: str
    semesterId: str
    sectionId: str
    parentName: str | None = None
    parentPhone: str | None = None
    enrollmentYear: int | None = Field(default=None, ge=1990, le=2100)


class StudentUpdate(BaseModel):
    firstName: str | None = None
    lastName: str | None = None
    phone: str | None = None
    departmentId: str | None = None
    semesterId: str | None = None
    sectionId: str | None = None
    parentName: str | None = None
    parentPhone: str | None = None
    isActive: bool | None = None
