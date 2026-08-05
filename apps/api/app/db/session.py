from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

_is_postgres = settings.database_url.startswith("postgresql")
engine_kwargs: dict = {"pool_pre_ping": True}
if _is_postgres:
    engine_kwargs.update(pool_size=20, max_overflow=10)

engine = create_async_engine(settings.database_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: one session per request."""
    async with AsyncSessionLocal() as session:
        yield session
