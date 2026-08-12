import os
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Read connection string securely from environment variable
RENDER_DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/gate_db"
)

if RENDER_DB_URL.startswith("postgresql://"):
    ASYNC_DB_URL = RENDER_DB_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif RENDER_DB_URL.startswith("postgres://"):
    ASYNC_DB_URL = RENDER_DB_URL.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    ASYNC_DB_URL = RENDER_DB_URL


@pytest.mark.asyncio
async def test_render_postgres_connection():
    """Verify asynchronous connection and basic query execution on PostgreSQL."""
    engine = create_async_engine(ASYNC_DB_URL, echo=False)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        val = result.scalar()
        assert val == 1, f"Expected 1, got {val}"
    await engine.dispose()
