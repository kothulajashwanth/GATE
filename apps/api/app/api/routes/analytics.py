from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_roles
from app.core.errors import NotFoundError
from app.db.models.student import Student
from app.db.models.user import Role, User
from app.db.session import get_db
from app.services.analytics import AnalyticsService
from app.services.audit import AuditService

router = APIRouter()


@router.get("/overview", summary="Admin overview KPIs & score distribution")
async def get_overview_kpis(
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    days: int = 30,
) -> dict:
    svc = AnalyticsService(db)
    data = await svc.get_overview_kpis(days=days)
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="ANALYTICS_VIEWED",
        entity_type="analytics",
        new_value={"days": days},
    )
    await db.commit()
    return data


@router.get("/departments", summary="Department performance metrics")
async def get_department_analytics(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    svc = AnalyticsService(db)
    return await svc.get_department_analytics()


@router.get("/questions", summary="Question quality & usage analytics")
async def get_question_analytics(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    svc = AnalyticsService(db)
    return await svc.get_question_analytics()


@router.get("/security", summary="Security proctoring violation analytics")
async def get_security_analytics(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    svc = AnalyticsService(db)
    return await svc.get_security_analytics()


@router.get("/export", response_class=PlainTextResponse, summary="Download CSV analytics report")
async def export_analytics_report(
    request: Request,
    actor: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    svc = AnalyticsService(db)
    csv_content = await svc.generate_csv_report()
    await AuditService.log(
        db,
        actor=actor,
        request=request,
        action="REPORT_EXPORTED",
        entity_type="report",
        new_value={"format": "csv"},
    )
    await db.commit()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=gate_ignite_analytics_report.csv"},
    )


@router.get("/students/me/analytics", summary="Student personal performance intelligence")
async def get_student_me_analytics(
    user: Annotated[User, Depends(require_roles(Role.STUDENT))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    student = (await db.execute(select(Student).where(Student.user_id == user.id))).scalar_one_or_none()
    if not student:
        raise NotFoundError("Student profile not found")

    svc = AnalyticsService(db)
    return await svc.get_student_personal_analytics(student.id)


@router.get("/audit-logs", summary="Get recent system audit logs for admin")
async def get_audit_logs(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
) -> list[dict]:
    from app.db.models.audit import AuditLog
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    logs = res.scalars().all()
    return [
        {
            "id": str(l.id),
            "action": l.action,
            "entityType": l.entity_type,
            "entityId": str(l.entity_id) if l.entity_id else None,
            "actorId": str(l.actor_id) if l.actor_id else None,
            "actorEmail": l.actor.email if l.actor else "System",
            "ipAddress": l.ip_address,
            "createdAt": l.created_at.isoformat() if l.created_at else None,
        }
        for l in logs
    ]