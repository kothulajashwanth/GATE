from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging
from app.core.middleware import setup_middleware
from app.db.redis import close_redis

settings = get_settings()
setup_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_redis()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Secure online examination management API with AI question generation and live proctoring.",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None if settings.is_production else "/redoc",
    lifespan=lifespan,
)

if settings.is_production:
    app.add_middleware(HTTPSRedirectMiddleware)

from app.api.routes.health import router as health_router

setup_middleware(app)
register_error_handlers(app)

app.include_router(health_router, tags=["health"])
app.include_router(api_router, prefix="/api/v1")
