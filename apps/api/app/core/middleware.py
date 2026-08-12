import re
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import RateLimitError
from app.db.redis import get_redis


class TrailingSlashAndCorsMiddleware(BaseHTTPMiddleware):
    """
    1. Normalizes trailing slashes in-place so FastAPI routing matches without issuing 301/307 redirects.
    2. Intercepts OPTIONS preflight requests to guarantee a 200 OK response with correct CORS headers,
       preventing any downstream middleware or routing from triggering a preflight redirect error.
    """

    async def dispatch(self, request: Request, call_next):
        # Normalize trailing slash in-place
        path = request.scope.get("path", "")
        if path != "/" and path.endswith("/"):
            request.scope["path"] = path.rstrip("/")

        settings = get_settings()
        origin = request.headers.get("origin")

        allowed = settings.cors_origins
        is_allowed = False
        if origin:
            if origin in allowed or "*" in allowed:
                is_allowed = True
            elif re.match(r"^https://[a-zA-Z0-9-]+\.vercel\.app$", origin):
                is_allowed = True
            elif origin.endswith(".vercel.app"):
                is_allowed = True

        cors_origin = origin if (is_allowed and origin) else "https://fabgate.vercel.app"

        # Intercept preflight OPTIONS requests directly
        if request.method == "OPTIONS":
            req_headers = request.headers.get(
                "access-control-request-headers",
                "Authorization, Content-Type, X-Request-Id, X-Internal-Key, Accept, Origin, X-Requested-With",
            )

            headers = {
                "Access-Control-Allow-Origin": cors_origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": req_headers,
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "600",
            }
            return Response(status_code=200, headers=headers)

        # For non-OPTIONS requests, execute call_next and attach CORS headers to the response
        try:
            response = await call_next(request)
        except Exception as exc:
            import logging
            logging.getLogger("app").exception(f"Unhandled exception in request processing: {exc}")
            response = JSONResponse(
                status_code=500,
                content={"error": {"code": "internal_error", "message": str(exc)}},
            )

        if origin or is_allowed:
            response.headers["Access-Control-Allow-Origin"] = cors_origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Expose-Headers"] = "X-Request-Id, X-Response-Time-Ms"

        return response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id and logs the request/response summary."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), fullscreen=(self)"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limit keyed by client IP, backed by Redis.

    ponytail: per-IP fixed window in Redis; move to token bucket when traffic grows.
    """

    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if settings.environment == "development":
            return await call_next(request)

        redis = get_redis()
        client_ip = request.client.host if request.client else "unknown"
        key = f"rl:{client_ip}"
        try:
            count = await redis.incr(key)
            if count == 1:
                await redis.expire(key, settings.rate_limit_window_seconds)
            if count > settings.rate_limit_requests:
                raise RateLimitError()
        except RateLimitError:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "rate_limited", "message": "Too many requests"}},
                headers={"Retry-After": str(settings.rate_limit_window_seconds)},
            )
        return await call_next(request)


def setup_middleware(app: FastAPI) -> None:
    settings = get_settings()

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-Id", "X-Response-Time-Ms"],
        max_age=600,
    )
    app.add_middleware(TrailingSlashAndCorsMiddleware)

