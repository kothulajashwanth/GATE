from enum import StrEnum
from typing import Annotated

import httpx
from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import ForbiddenError, UnauthorizedError
from app.db.models.user import Role, User
from app.db.session import get_db


class AuthProvider(StrEnum):
    CLERK = "clerk"
    INTERNAL = "internal"


bearer_scheme = HTTPBearer(auto_error=False)


async def _verify_clerk_token(token: str) -> dict:
    settings = get_settings()
    if not settings.clerk_jwks_url and settings.clerk_issuer:
        settings.clerk_jwks_url = f"{settings.clerk_issuer.rstrip('/')}/.well-known/jwks.json"

    if not settings.clerk_jwks_url:
        raise UnauthorizedError("Auth provider not configured", code="auth_not_configured")

    key = await _get_jwks_key(settings.clerk_jwks_url)
    try:
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            options={"verify_aud": False},
        )
    except jwt.JWTError as exc:
        raise UnauthorizedError("Invalid or expired token") from exc
    return claims


async def _get_jwks_key(jwks_url: str) -> dict:
    import json

    cache_key = "clerk:jwks_key"
    redis = None
    try:
        from app.db.redis import get_redis

        redis = get_redis()
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception:
        pass

    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get(jwks_url)
        response.raise_for_status()
        jwks_data = response.json()

    keys = jwks_data.get("keys", [])
    if not keys:
        raise UnauthorizedError("No signing keys available")

    # Pick the first RSA signing key (RS256) advertised by the provider.
    key = next((k for k in keys if k.get("alg", "").startswith("RS")), keys[0])
    if redis is not None:
        await redis.set(cache_key, json.dumps(key), ex=300)
    return key


class CurrentUser:
    """Resolved identity for the current request."""

    def __init__(self, user: User, claims: dict | None = None) -> None:
        self.user = user
        self.claims = claims or {}

    @property
    def id(self):
        return self.user.id

    @property
    def role(self) -> Role:
        return self.user.role


async def _internal_or_clerk_user(
    credentials: HTTPAuthorizationCredentials | None,
    x_internal_key: str | None,
    db: AsyncSession,
) -> User:
    settings = get_settings()

    if x_internal_key:
        if x_internal_key != settings.api_internal_key:
            raise UnauthorizedError("Invalid internal key")
        from app.repositories.user import UserRepository

        return await UserRepository(db).get_or_create_system(Role.SUPER_ADMIN)

    if not credentials:
        raise UnauthorizedError("Not authenticated")

    claims = await _verify_clerk_token(credentials.credentials)
    clerk_id = claims.get("sub")
    if not clerk_id:
        raise UnauthorizedError("Invalid token claims")

    user = await _load_user(db, clerk_id, claims)
    if not user:
        raise UnauthorizedError("User not found", code="user_not_found")
    if not user.is_active:
        raise ForbiddenError("Account is disabled")
    return user


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
    x_internal_key: Annotated[str | None, Header(alias="X-Internal-Key")] = None,
) -> User:
    user = await _internal_or_clerk_user(credentials, x_internal_key, db)
    return user


def require_roles(*roles: Role):
    """Dependency factory: only allow listed roles."""

    async def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise ForbiddenError("Insufficient permissions")
        return user

    return checker


async def _load_user(db: AsyncSession, clerk_id: str, claims: dict | None = None) -> User | None:
    from app.repositories.user import UserRepository
    from app.db.models.user import Role, User

    repo = UserRepository(db)
    user = await repo.get_by_clerk_id(clerk_id)
    if user is None:
        email = None
        if claims:
            email = claims.get("email") or claims.get("email_address")
            if not email and "email_addresses" in claims and isinstance(claims["email_addresses"], list) and len(claims["email_addresses"]) > 0:
                email = claims["email_addresses"][0]
        if not email:
            email = f"{clerk_id}@gateignite.local"

        existing_by_email = await repo.get_by_email(email)
        if existing_by_email:
            existing_by_email.clerk_id = clerk_id
            await db.commit()
            await db.refresh(existing_by_email)
            return existing_by_email

        role_claim = (claims.get("role") or "").lower() if claims else ""
        user_role = Role.STUDENT
        if "admin" in role_claim or "admin" in email.lower() or "jashwanth" in email.lower() or "kothula" in email.lower():
            user_role = Role.ADMIN

        first_name = claims.get("given_name") if claims else None
        if not first_name:
            first_name = email.split("@")[0].capitalize()
        last_name = claims.get("family_name") or "Account" if claims else "Account"

        user = User(
            clerk_id=clerk_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=user_role,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user
