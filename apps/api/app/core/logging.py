import logging
import sys
from typing import Any

import structlog


def setup_logging(level: str = "INFO") -> None:
    """Configure structlog with JSON output in production, pretty console otherwise."""
    shared: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    logging.basicConfig(stream=sys.stdout, level=getattr(logging, level.upper(), logging.INFO))

    structlog.configure(
        processors=shared + [structlog.processors.JSONRenderer()],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
