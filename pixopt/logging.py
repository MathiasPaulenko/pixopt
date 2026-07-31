"""Structured logging support for pixopt.

Provides an optional structured logger that library consumers can
configure.  By default, logging is silent (``NullHandler``).

Enable logging via::

    import logging
    logging.getLogger("pixopt").setLevel(logging.DEBUG)

Or use the convenience function::

    from pixopt.logging import configure_logging
    configure_logging(level="DEBUG")
"""

from __future__ import annotations

import json
import logging
from typing import Any

__all__ = ["configure_logging", "get_logger", "StructuredFormatter"]

_LOGGER_NAME = "pixopt"


class StructuredFormatter(logging.Formatter):
    """JSON-line formatter for structured log records."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach extra fields if present.
        for key in ("path", "operation", "width", "height", "size_bytes", "format", "elapsed"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a pixopt logger instance.

    Args:
        name: Optional sub-logger name (appended to ``"pixopt"``).

    Returns:
        A :class:`logging.Logger` configured with a ``NullHandler``.

    """
    logger_name = f"{_LOGGER_NAME}.{name}" if name else _LOGGER_NAME
    logger = logging.getLogger(logger_name)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
    return logger


def configure_logging(
    *,
    level: str | int = "INFO",
    structured: bool = True,
    log_file: str | None = None,
) -> logging.Logger:
    """Configure pixopt logging.

    Args:
        level: Logging level (e.g. ``"DEBUG"``, ``"INFO"``).
        structured: If True, emit JSON-formatted log lines.
        log_file: Optional file path. If None, logs go to stderr.

    Returns:
        The configured root pixopt logger.

    """
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)

    # Remove all existing handlers to avoid duplicates.
    for _handler in list(logger.handlers):
        logger.removeHandler(_handler)

    handler: logging.Handler
    if log_file is not None:
        handler = logging.FileHandler(log_file, encoding="utf-8")
    else:
        handler = logging.StreamHandler()

    if structured:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"),
        )

    logger.addHandler(handler)
    logger.propagate = False
    return logger
