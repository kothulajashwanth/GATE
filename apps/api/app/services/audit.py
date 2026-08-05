
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditLog
from app.db.models.user import User


class AuditService:
    """Append-only audit trail for admin actions. Fire-and-forget per request.

    ponytail: single insert per action; switch to a background queue when
    audit volume becomes a concern.
    """

    @staticmethod
    async def log(
        db: AsyncSession,
        *,
        actor: User | None,
        request: Request | None,
        action: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        details: str | None = None,
    ) -> None:
        entry = AuditLog(
            actor_id=actor.id if actor else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
            details=details,
        )
        db.add(entry)
        # The caller commits the transaction; nothing extra to do here.
