from __future__ import annotations

import sys

import structlog


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(**bind: object) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger("rag").bind(**bind)
