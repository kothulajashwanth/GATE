from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_roles
from app.db.models.user import Role, User
from app.db.session import get_db

router = APIRouter()


class MeResponse(BaseModel):
    id: str
    email: str
    firstName: str | None
    lastName: str | None
    role: str
    avatarUrl: str | None
    isActive: bool


def _to_me(user: User) -> MeResponse:
    return MeResponse(
        id=str(user.id),
        email=user.email,
        firstName=user.first_name,
        lastName=user.last_name,
        role=user.role.value,
        avatarUrl=user.avatar_url,
        isActive=user.is_active,
    )


@router.get("/me", response_model=MeResponse, summary="Current user")
async def me(user: Annotated[User, Depends(get_current_user)]) -> MeResponse:
    return _to_me(user)


@router.get("", response_model=list[MeResponse], summary="List users (admin)")
async def list_users(
    _: Annotated[User, Depends(require_roles(Role.ADMIN, Role.SUPER_ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[MeResponse]:
    result = await db.execute(select(User).order_by(User.created_at.desc()).limit(100))
    return [_to_me(u) for u in result.scalars().all()]
