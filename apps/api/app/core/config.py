from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings, loaded from environment / .env. One source of truth."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- Core ----
    app_name: str = "ExamShield API"
    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = "INFO"
    secret_key: str = "dev-secret-key-change-me"

    # ---- Database ----
    database_url: str = "postgresql+asyncpg://examshield:examshield_dev@localhost:5432/examshield"

    # ---- Redis ----
    redis_url: str = "redis://localhost:6379/0"

    # ---- Storage (S3-compatible; Supabase Storage in prod) ----
    storage_provider: str = "minio"
    storage_endpoint: str = "http://localhost:9000"
    storage_public_url: str = "http://localhost:9000"
    storage_bucket: str = "examshield"
    storage_region: str = "us-east-1"
    storage_access_key: str = "examshield"
    storage_secret_key: str = "examshield_dev"

    # ---- Auth / Security ----
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # ---- Clerk (identity provider) ----
    clerk_secret_key: str | None = None
    clerk_issuer: str | None = None
    clerk_jwks_url: str | None = None

    # ---- AI ----
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"
    ai_provider: Literal["openai", "gemini", "mock"] = "mock"

    # ---- Email ----
    resend_api_key: str | None = None
    email_from: str = "ExamShield <no-reply@example.com>"

    # ---- Internal ----
    api_internal_key: str = "change-me-internal-key"
    allowed_origins: str = "http://localhost:3000,http://localhost:3001"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
