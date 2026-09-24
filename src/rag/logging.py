from __future__ import annotations

import sys

import structlog


class _CurrentStderr:
    """Always the process stderr, even after pytest replaces it."""

    def write(self, message: str) -> int:
        return sys.stderr.write(message)

    def flush(self) -> None:
        sys.stderr.flush()


def configure_logging() -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        logger_factory=structlog.PrintLoggerFactory(file=_CurrentStderr()),
        cache_logger_on_first_use=False,
    )


def get_logger(**bind: object) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger("rag").bind(**bind)
