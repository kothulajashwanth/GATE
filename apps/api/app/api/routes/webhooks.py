from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import UnauthorizedError
from app.core.logging import get_logger
from app.db.models.user import Role, User
from app.db.session import get_db

router = APIRouter()
logger = get_logger("webhooks")


class ClerkWebhookBody(BaseModel):
    event: str
    data: dict[str, Any]


_ROLE_MAP: dict[str, Role] = {
    "super_admin": Role.SUPER_ADMIN,
    "admin": Role.ADMIN,
    "student": Role.STUDENT,
    "faculty": Role.FACULTY,
}


def _role_from_metadata(data: dict[str, Any]) -> Role:
    meta = data.get("public_metadata") or {}
    role_name = meta.get("role", "student")
    return _ROLE_MAP.get(str(role_name), Role.STUDENT)


def _normalize_user(data: dict[str, Any]) -> dict[str, Any]:
    primary_email = data.get("email_addresses") or []
    email = next((e.get("email_address") for e in primary_email if e.get("id") == data.get("primary_email_address_id")), None)
    if not email and primary_email:
        email = primary_email[0].get("email_address")
    if not email:
        email = data.get("email") or data.get("primary_email_address") or ""

    return {
        "clerk_id": data.get("id"),
        "email": email,
        "first_name": data.get("first_name"),
        "last_name": data.get("last_name"),
        "avatar_url": data.get("image_url"),
        "role": _role_from_metadata(data),
        "is_active": True,
    }


async def _find_by_clerk(db: AsyncSession, clerk_id: str) -> User | None:
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    return result.scalar_one_or_none()


async def _handle_upsert(db: AsyncSession, data: dict[str, Any]) -> None:
    payload = _normalize_user(data)
    user = await _find_by_clerk(db, payload["clerk_id"])
    if user:
        user.email = payload["email"]
        user.first_name = payload["first_name"]
        user.last_name = payload["last_name"]
        user.avatar_url = payload["avatar_url"]
        user.role = payload["role"]
    else:
        db.add(User(**payload))
    await db.commit()


async def _handle_delete(db: AsyncSession, data: dict[str, Any]) -> None:
    user = await _find_by_clerk(db, data.get("id", ""))
    if user:
        user.deleted_at = datetime.now(UTC)
        user.is_active = False
        await db.commit()


@router.post("/clerk", summary="Clerk identity webhook (user.created/updated/deleted)")
async def clerk_webhook(
    body: ClerkWebhookBody,
    request: Request,
    x_internal_key: str | None = Header(default=None, alias="X-Internal-Key"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    settings = get_settings()
    # Webhook sync uses the internal key; the Svix signature is verified in the
    # web layer. Reject unknown senders here.
    if not x_internal_key or x_internal_key != settings.api_internal_key:
        raise UnauthorizedError("Invalid internal key")

    event = body.event
    data = body.data
    logger.info("clerk_event", event_name=event, clerk_id=data.get("id"))

    if event in ("user.created", "user.updated"):
        await _handle_upsert(db, data)
    elif event == "user.deleted":
        await _handle_delete(db, data)
    else:
        logger.debug("unhandled_clerk_event", event=event)

    return {"received": True}
