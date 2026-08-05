from fastapi import APIRouter, Depends
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import get_redis_dep
from app.db.session import get_db

router = APIRouter()


class HealthStatus(BaseModel):
    status: str
    version: str
    database: str
    redis: str


@router.get("/health", response_model=HealthStatus, summary="Service health")
async def health(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis_dep),
) -> HealthStatus:
    db_ok = redis_ok = "up"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_ok = "down"
    try:
        await redis.ping()
    except Exception:
        redis_ok = "down"
    return HealthStatus(
        status="ok" if db_ok == redis_ok == "up" else "degraded",
        version="0.1.0",
        database=db_ok,
        redis=redis_ok,
    )
