from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger("errors")


class AppError(Exception):
    """Base domain error. Carries an HTTP status, a stable error code and details."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "app_error",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message, code="not_found", status_code=status.HTTP_404_NOT_FOUND, details=details)


class ConflictError(AppError):
    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message, code="conflict", status_code=status.HTTP_409_CONFLICT, details=details)


class ForbiddenError(AppError):
    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message, code="forbidden", status_code=status.HTTP_403_FORBIDDEN, details=details)


class UnauthorizedError(AppError):
    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message, code="unauthorized", status_code=status.HTTP_401_UNAUTHORIZED, details=details)


class ValidationError(AppError):
    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message, code="validation_error", status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, details=details)


class RateLimitError(AppError):
    def __init__(self, message: str = "Too many requests", *, details: Any = None) -> None:
        super().__init__(message, code="rate_limited", status_code=status.HTTP_429_TOO_MANY_REQUESTS, details=details)


def _error_body(status_code: int, code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
        "status": status_code,
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.status_code, exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "loc": list(e.get("loc", [])),
                "msg": e.get("msg", "Invalid value"),
                "type": e.get("type", "error"),
            }
            for e in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content=_error_body(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "validation_error",
                "Request validation failed",
                errors,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception", path=str(request.url), error=str(exc), exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                "internal_error",
                "An internal error occurred",
            ),
        )
