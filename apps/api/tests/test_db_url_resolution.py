import os
from sqlalchemy.engine import make_url

from app.core.config import Settings, _resolve_env_placeholders


def test_resolve_env_placeholders_with_literal_postgres_port():
    raw_url = "postgresql://user:pass@host:${POSTGRES_PORT}/dbname"
    resolved = _resolve_env_placeholders(raw_url)
    assert "${POSTGRES_PORT}" not in resolved
    assert ":5432/" in resolved

    parsed_url = make_url(resolved)
    assert parsed_url.port == 5432
    assert type(parsed_url.port) is int


def test_settings_async_database_url_resolution():
    os.environ["DATABASE_URL"] = "postgresql://myuser:mypass@myhost:${POSTGRES_PORT}/mydb"
    settings = Settings()
    async_url = settings.async_database_url

    assert async_url.startswith("postgresql+asyncpg://")
    parsed_url = make_url(async_url)
    assert parsed_url.port == 5432
    assert type(parsed_url.port) is int
    assert parsed_url.username == "myuser"
    assert parsed_url.host == "myhost"
    assert parsed_url.database == "mydb"

    # Clean up test env var override
    del os.environ["DATABASE_URL"]
