from io import BytesIO
import os
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.errors import NotFoundError, ValidationError
from app.db.models.question import FailedQuestion, QuestionBankFolder, Subject, UploadedFile
from app.db.models.user import Role, User
from app.db.session import get_db
from app.services.audit import AuditService
from app.services.document_parser import process_uploaded_document
from app.services.question_service import QuestionService

router = APIRouter()

UPLOAD_DIR = os.path.join(os.getcwd(), "uploads", "questions")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class SubjectOut(BaseModel):
    id: str
    name: str
    code: str
    description: str | None = None
    departmentId: str | None = None


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    code: str = Field(min_length=1, max_length=20)
    description: str | None = None
    departmentId: str | None = None


class FolderOut(BaseModel):
    id: str
    name: str
    parentId: str | None = None


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    parentId: str | None = None


class UploadedFileOut(BaseModel):
    id: str
    fileName: str
    originalName: str
    fileType: str
    fileSize: str
    status: str
    questionsFound: int
    ocrUsed: bool
    createdAt: str


def _file_out(uf: UploadedFile) -> UploadedFileOut:
    size_str = f"{round(uf.file_size / 1024, 1)} KB" if uf.file_size < 1024 * 1024 else f"{round(uf.file_size / (1024 * 1024), 2)} MB"
    return UploadedFileOut(
        id=str(uf.id),
        fileName=uf.file_name,
        originalName=uf.original_name,
        fileType=uf.file_type.lower(),
        fileSize=size_str,
        status=uf.status.lower(),
        questionsFound=uf.questions_found,
        ocrUsed=uf.ocr_used,
        createdAt=uf.created_at.isoformat(),
    )


@router.get("/subjects", response_model=list[SubjectOut], summary="List subjects")
async def list_subjects(db: Annotated[AsyncSession, Depends(get_db)]) -> list[SubjectOut]:
    result = await db.execute(select(Subject).where(Subject.deleted_at.is_(None)).order_by(Subject.name).limit(200))
    return [SubjectOut(id=str(s.id), name=s.name, code=s.code, description=s.description, departmentId=str(s.department_id) if s.department_id else None) for s in result.scalars().all()]


@router.post("/subjects", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
async def create_subject(
    body: SubjectCreate,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SubjectOut:
    existing = await db.execute(select(Subject).where(Subject.code == body.code))
    if existing.scalar_one_or_none():
        raise ValidationError("Subject code already exists")
    subject = Subject(name=body.name, code=body.code, description=body.description, department_id=body.departmentId)
    db.add(subject)
    await db.flush()
    await AuditService.log(db, actor=actor, request=request, action="subject.create", entity_type="subject", entity_id=str(subject.id), new_value=body.model_dump(mode="json"))
    await db.commit()
    return SubjectOut(id=str(subject.id), name=subject.name, code=subject.code, description=subject.description, departmentId=str(subject.department_id) if subject.department_id else None)


@router.get("/folders", response_model=list[FolderOut], summary="List question bank folders")
async def list_folders(db: Annotated[AsyncSession, Depends(get_db)]) -> list[FolderOut]:
    result = await db.execute(select(QuestionBankFolder).where(QuestionBankFolder.deleted_at.is_(None)).order_by(QuestionBankFolder.name).limit(200))
    return [FolderOut(id=str(f.id), name=f.name, parentId=str(f.parent_id) if f.parent_id else None) for f in result.scalars().all()]


@router.get("/files", response_model=list[UploadedFileOut], summary="List uploaded question files")
async def list_uploaded_files(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[UploadedFileOut]:
    files = await QuestionService(db).list_files()
    return [_file_out(f) for f in files]


@router.post("/files", response_model=UploadedFileOut, status_code=status.HTTP_201_CREATED, summary="Upload question document (PDF, DOCX, TXT, XLSX)")
async def upload_question_file(
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
) -> UploadedFileOut:
    ext = file.filename.lower().split('.')[-1] if file.filename else ""
    if ext not in ["pdf", "docx", "txt", "xlsx", "xls"]:
        raise ValidationError(f"Unsupported file type .{ext}. Allowed types: .pdf, .docx, .txt, .xlsx")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:  # 20MB limit
        raise ValidationError("File size exceeds 20MB limit")

    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    storage_path = os.path.join(UPLOAD_DIR, unique_filename)
    with open(storage_path, "wb") as f:
        f.write(content)

    service = QuestionService(db)
    uf = await service.create_uploaded_file(
        file_name=unique_filename,
        original_name=file.filename or "uploaded_file",
        file_type=ext,
        file_size=len(content),
        storage_url=storage_path,
        uploaded_by=actor.id,
    )

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="QUESTION_FILE_UPLOADED",
        entity_type="uploaded_file",
        entity_id=str(uf.id),
        new_value={"filename": file.filename, "size": len(content)},
    )
    await db.commit()
    await db.refresh(uf)
    return _file_out(uf)


@router.post("/files/{file_id}/process", summary="Process & parse uploaded file into questions with preview")
async def process_file(
    file_id: str,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = QuestionService(db)
    uf = await service.get_file(file_id)

    if not uf.storage_url or not os.path.exists(uf.storage_url):
        raise NotFoundError("Stored file content not found")

    with open(uf.storage_url, "rb") as f:
        file_bytes = f.read()

    extraction = await process_uploaded_document(db, file_bytes, uf.original_name)

    # Record failed questions in database table
    for failed_item in extraction.failed_questions:
        fq = FailedQuestion(
            source_file_id=uf.id,
            raw_data={"raw": failed_item.get("raw_data", "")},
            reason=failed_item.get("reason", "PARSER_ERROR"),
        )
        db.add(fq)

    uf.questions_found = len(extraction.questions)
    uf.ocr_used = extraction.ocr_used
    if extraction.ocr_required:
        uf.status = "OCR_REQUIRED"
    elif extraction.review_count > 0:
        uf.status = "REVIEW_REQUIRED"
    else:
        uf.status = "PARSED"

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="QUESTION_FILE_PROCESSED",
        entity_type="uploaded_file",
        entity_id=str(uf.id),
        new_value={
            "total": extraction.total,
            "valid": extraction.valid_count,
            "review": extraction.review_count,
            "failed": extraction.failed_count,
        },
    )
    await db.commit()

    return {
        "file_id": str(uf.id),
        "status": uf.status,
        "total": extraction.total,
        "valid_count": extraction.valid_count,
        "review_count": extraction.review_count,
        "failed_count": extraction.failed_count,
        "ocr_required": extraction.ocr_required,
        "questions": extraction.questions,
        "failed_questions": extraction.failed_questions,
    }


class ImportConfirmBody(BaseModel):
    questions: list[dict]
    subjectId: str | None = None
    folderId: str | None = None


@router.post("/import/{file_id}/confirm", summary="Confirm & save reviewed questions into PostgreSQL")
async def confirm_import(
    file_id: str,
    body: ImportConfirmBody,
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    service = QuestionService(db)
    created_questions = await service.confirm_import(
        file_id=file_id,
        actor=actor,
        questions_data=body.questions,
        subject_id=body.subjectId,
        folder_id=body.folderId,
    )

    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="QUESTION_IMPORT_CONFIRMED",
        entity_type="uploaded_file",
        entity_id=file_id,
        new_value={"imported_count": len(created_questions)},
    )
    await db.commit()

    return {
        "file_id": file_id,
        "status": "COMPLETED",
        "imported_count": len(created_questions),
        "question_ids": [str(q.id) for q in created_questions],
    }


@router.post("/upload-document", summary="Legacy upload and parse question document")
async def upload_document_legacy(
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    subject_id: str | None = None,
) -> dict:
    content = await file.read()
    extraction = await process_uploaded_document(db, content, file.filename or "file.pdf")
    return {
        "filename": file.filename,
        "total_parsed": len(extraction.questions),
        "questions": extraction.questions,
    }