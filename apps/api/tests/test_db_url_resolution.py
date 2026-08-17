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
    get_settings.cache_clear()


def test_alembic_config_with_percent_in_url():
    from alembic.config import Config

    os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres.zamewnqegiszvekkzteq:Fab%407025@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
    get_settings.cache_clear()

    cfg = Config("alembic.ini")
    database_url = get_settings().async_database_url.replace("%", "%%")
    cfg.set_main_option("sqlalchemy.url", database_url)

    # Check that retrieving the option returns unescaped %40 without throwing ValueError: invalid interpolation syntax
    retrieved_url = cfg.get_main_option("sqlalchemy.url")
    assert retrieved_url == "postgresql+asyncpg://postgres.zamewnqegiszvekkzteq:Fab%407025@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"

    del os.environ["DATABASE_URL"]
    get_settings.cache_clear()

