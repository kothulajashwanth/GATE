from datetime import UTC, datetime, timedelta
from typing import Annotated
import json

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.core.auth import get_current_user
from app.core.config import get_settings
from app.db.models.user import User, Role
from app.db.redis import get_redis_dep
from app.db.session import get_db
from app.schemas.active_session import StudentSessionData

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
    redis: Annotated[Redis, Depends(get_redis_dep)],
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

    # Record active student session in Redis
    if user.role == Role.STUDENT:
        session_data = StudentSessionData(
            user_id=user.id,
            login_time=datetime.now(UTC),
            last_activity=datetime.now(UTC),
            status="logged_in"
        )
        await redis.set(
            f"active_student_sessions:{user.id}",
            session_data.model_dump_json(), # Using model_dump_json for Pydantic v2
            ex=exp_minutes * 60 # Set TTL same as token expiry
        )

    return TokenResponse(access_token=token, expires_in=exp_minutes * 60)


@router.get("/me", response_model=TokenResponse, summary="Current user (alias)")
async def me_token(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis_dep)], # Add redis dependency here too for consistency
) -> TokenResponse:
    return await mint_token(request, user, db, redis)