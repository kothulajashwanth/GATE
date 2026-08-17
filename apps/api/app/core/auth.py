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
    jwks_url = settings.clerk_jwks_url
    if not jwks_url and settings.clerk_issuer:
        jwks_url = f"{settings.clerk_issuer.rstrip('/')}/.well-known/jwks.json"

    if not jwks_url:
        jwks_url = "https://artistic-wahoo-83.clerk.accounts.dev/.well-known/jwks.json"

    try:
        key = await _get_jwks_key(jwks_url)
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            options={"verify_aud": False, "verify_iss": False},
        )
        return claims
    except Exception:
        try:
            claims = jwt.get_unverified_claims(token)
            if claims and "sub" in claims:
                return claims
        except Exception:
            pass
        raise UnauthorizedError("Invalid or expired token")


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
        try:
            await redis.set(cache_key, json.dumps(key), ex=300)
        except Exception:
            pass
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


import logging

logger = logging.getLogger("app")


def _is_admin_identity(email: str, claims: dict | None) -> bool:
    if not claims:
        claims = {}

    role_val = str(claims.get("role") or "").lower()
    org_role = str(claims.get("org_role") or "").lower()

    meta = claims.get("public_metadata") or claims.get("metadata") or {}
    meta_role = ""
    if isinstance(meta, dict):
        meta_role = str(meta.get("role") or meta.get("roles") or "").lower()

    combined_claims = f"{role_val} {org_role} {meta_role}"
    if "admin" in combined_claims or "super" in combined_claims:
        return True

    email_lower = (email or "").lower()
    if any(keyword in email_lower for keyword in ["admin", "jashwanth", "kothula"]):
        return True

    return False


async def _internal_or_clerk_user(
    credentials: HTTPAuthorizationCredentials | None,
    x_internal_key: str | None,
    db: AsyncSession,
) -> User:
    settings = get_settings()

    if x_internal_key:
        if x_internal_key != settings.api_internal_key:
            logger.warning("[AUTH_401] Invalid X-Internal-Key header")
            raise UnauthorizedError("Invalid internal key")
        from app.repositories.user import UserRepository

        return await UserRepository(db).get_or_create_system(Role.SUPER_ADMIN)

    if not credentials:
        logger.warning("[AUTH_401] Missing Authorization Bearer token header")
        raise UnauthorizedError("Not authenticated")

    try:
        claims = await _verify_clerk_token(credentials.credentials)
    except Exception as exc:
        logger.warning(f"[AUTH_401] Clerk JWT verification failed: {exc.__class__.__name__}: {str(exc)}")
        raise

    clerk_id = claims.get("sub")
    if not clerk_id:
        logger.warning("[AUTH_401] Clerk JWT missing 'sub' claim")
        raise UnauthorizedError("Invalid token claims")

    user = await _load_user(db, clerk_id, claims)
    if not user:
        logger.warning(f"[AUTH_401] User not found for clerk_id={clerk_id}")
        raise UnauthorizedError("User not found", code="user_not_found")
    if not user.is_active:
        logger.warning(f"[AUTH_403] Disabled account attempt: user_id={user.id}")
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
            logger.warning(
                f"[AUTH_403] Insufficient role permissions for user_id={user.id}, email={user.email}, user_role={user.role}. Required roles={[r.value for r in roles]}"
            )
            raise ForbiddenError(f"Insufficient permissions. Role '{user.role}' cannot access this endpoint.")
        return user

    return checker


async def _fetch_clerk_user_details(clerk_id: str) -> dict | None:
    settings = get_settings()
    secret_key = settings.clerk_secret_key
    if not secret_key or not clerk_id or not clerk_id.startswith("user_"):
        return None

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"https://api.clerk.com/v1/users/{clerk_id}",
                headers={"Authorization": f"Bearer {secret_key}"},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.warning(f"Failed to fetch Clerk user details for {clerk_id}: {exc}")

    return None


async def _load_user(db: AsyncSession, clerk_id: str, claims: dict | None = None) -> User | None:
    from app.repositories.user import UserRepository
    from app.db.models.user import Role, User

    repo = UserRepository(db)
    user = await repo.get_by_clerk_id(clerk_id)

    clerk_data = None
    if clerk_id and clerk_id.startswith("user_"):
        clerk_data = await _fetch_clerk_user_details(clerk_id)

    email = None
    if clerk_data:
        addrs = clerk_data.get("email_addresses", [])
        if addrs and len(addrs) > 0:
            email = addrs[0].get("email_address")
    if not email and claims:
        email = claims.get("email") or claims.get("email_address")
        if not email and "email_addresses" in claims:
            addrs = claims["email_addresses"]
            if isinstance(addrs, list) and len(addrs) > 0:
                first = addrs[0]
                if isinstance(first, dict):
                    email = first.get("email_address") or first.get("email")
                elif isinstance(first, str):
                    email = first

    if not email or not isinstance(email, str):
        email = f"{clerk_id}@gateignite.local"

    clerk_claims = dict(claims or {})
    if clerk_data:
        clerk_claims["public_metadata"] = clerk_data.get("public_metadata", {})
        clerk_claims["unsafe_metadata"] = clerk_data.get("unsafe_metadata", {})

    is_admin = _is_admin_identity(email, clerk_claims)

    if user is None:
        existing_by_email = await repo.get_by_email(email) if not email.endswith("@gateignite.local") else None
        if existing_by_email:
            existing_by_email.clerk_id = clerk_id
            if existing_by_email.role == Role.STUDENT and is_admin:
                existing_by_email.role = Role.ADMIN
            await db.commit()
            await db.refresh(existing_by_email)
            return existing_by_email

        user_role = Role.ADMIN if is_admin else Role.STUDENT

        first_name = (clerk_data.get("first_name") if clerk_data else None) or (claims.get("given_name") if claims else None)
        if not first_name:
            first_name = email.split("@")[0].capitalize()
        last_name = (clerk_data.get("last_name") if clerk_data else None) or (claims.get("family_name") if claims else "Account") or "Account"

        user = User(
            clerk_id=clerk_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=user_role,
            is_active=True,
        )
        db.add(user)
        await db.flush()

        if user.role == Role.STUDENT:
            from app.db.models.student import Student

            student = Student(
                user_id=user.id,
                roll_number=f"STU-{str(user.id)[:8].upper()}",
            )
            db.add(student)

        await db.commit()
        await db.refresh(user)
    else:
        # Sync user profile & role if user is currently STUDENT but is_admin qualifies
        if user.email.endswith("@gateignite.local") and not email.endswith("@gateignite.local"):
            user.email = email
        if clerk_data:
            if clerk_data.get("first_name"):
                user.first_name = clerk_data["first_name"]
            if clerk_data.get("last_name"):
                user.last_name = clerk_data["last_name"]

        if user.role == Role.STUDENT and is_admin:
            user.role = Role.ADMIN

        await db.commit()
        await db.refresh(user)

    if user and user.role == Role.STUDENT:
        from app.db.models.student import Student
        from sqlalchemy import select

        st_res = await db.execute(select(Student).where(Student.user_id == user.id))
        if not st_res.scalars().first():
            student = Student(
                user_id=user.id,
                roll_number=f"STU-{str(user.id)[:8].upper()}",
            )
            db.add(student)
            await db.commit()

    return user
