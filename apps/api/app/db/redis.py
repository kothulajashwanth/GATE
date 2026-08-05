from collections.abc import AsyncGenerator

from redis.asyncio import Redis

from app.core.config import get_settings

settings = get_settings()

redis_client: Redis | None = None


def get_redis() -> Redis:
    """Lazily create the shared redis client."""
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(
            settings.redis_url, decode_responses=True, max_connections=50
        )
    return redis_client


async def close_redis() -> None:
    global redis_client
    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None


async def get_redis_dep() -> AsyncGenerator[Redis, None]:
    yield get_redis()
