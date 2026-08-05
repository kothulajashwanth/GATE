from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.models.notification import Notification
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.pagination import PaginatedResponse

router = APIRouter()


@router.get("", response_model=PaginatedResponse[dict], summary="Get user notifications")
async def get_notifications(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[dict]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    items = [
        {
            "id": str(n.id),
            "type": n.type.value,
            "title": n.title,
            "body": n.body,
            "isRead": n.is_read,
            "link": n.link,
            "createdAt": n.created_at.isoformat(),
        }
        for n in result.scalars().all()
    ]
    return PaginatedResponse(items=items, page=page, pageSize=page_size, total=len(items), totalPages=1)


@router.post("/mark-all-read", summary="Mark all notifications as read")
async def mark_all_read(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    result = await db.execute(
        select(Notification).where(Notification.user_id == user.id, Notification.is_read == False)
    )
    notifications = result.scalars().all()
    for n in notifications:
        n.is_read = True
    await db.commit()
    return {"success": True}
