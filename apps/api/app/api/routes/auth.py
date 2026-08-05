from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


@router.post("/token", response_model=TokenResponse, summary="Mint short-lived JWT for current session")
async def mint_token(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Returns a JWT signed with the app secret. Frontend uses this for API calls.

    The token contains: sub (user id), role, iat, exp.
    """
    settings = get_settings()
    exp_minutes = settings.access_token_expire_minutes
    exp = datetime.now(UTC) + timedelta(minutes=exp_minutes)
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "iat": int(datetime.now(UTC).timestamp()),
        "exp": int(exp.timestamp()),
    }
    import jwt as pyjwt

    token = pyjwt.encode(payload, settings.secret_key, algorithm="HS256")
    return TokenResponse(access_token=token, expires_in=exp_minutes * 60)


@router.get("/me", response_model=TokenResponse, summary="Current user (alias)")
async def me_token(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    return await mint_token(request, user, db)