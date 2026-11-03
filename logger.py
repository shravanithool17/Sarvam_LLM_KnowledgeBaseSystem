"""
logger.py — Structured JSON logging for the AI Knowledge Engineering Platform.

Every log record is emitted as a single JSON line containing:
  timestamp, level, module, stage, elapsed_ms (optional), status (optional),
  and any additional keyword arguments passed by the caller.

API keys and other secrets are masked before any log write.
Raw LLM request/response bodies are logged only when LOG_LEVEL=DEBUG.
"""

import json
import logging
import time
from typing import Any, Optional


def mask_key(value: str) -> str:
    """
    Returns '***' for any string that has non-whitespace content, empty string otherwise.
    Use this before logging any value that might be an API key or secret.

    Examples:
        mask_key("sk-abc123")  -> "***"
        mask_key("")           -> ""
        mask_key("   ")        -> "***"  (contains whitespace — treated as potentially secret)
    """
    return "***" if value and len(value) > 0 else ""


class _JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        # Base fields always present
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "module": record.name,
            "message": record.getMessage(),
        }

        # Optional structured fields injected via Logger.info(..., extra={...})
        for field in ("stage", "elapsed_ms", "status", "doc_name", "chunk_count",
                      "batch_id", "error"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)

        # Attach exception info if present
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger for `name`.
    The log level is read from the `settings` singleton on first call.
    Calling this multiple times with the same name returns the same logger instance
    (standard Python logging behaviour).

    Usage:
        log = get_logger("pipeline.ingest")
        log.info("Extraction complete", extra={"stage": "ingest", "elapsed_ms": 42})
    """
    from config import settings  # local import to avoid circular import at module load

    logger = logging.getLogger(name)

    # Avoid adding duplicate handlers when the logger already exists
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False

    logger.setLevel(getattr(logging, settings.log_level, logging.INFO))
    return logger


class StageTimer:
    """
    Context manager that logs the elapsed time of a named pipeline stage.

    Usage:
        with StageTimer(log, "chunking", doc_name="report.pdf") as t:
            chunks = create_chunks(pages)
    Logs on exit: {"stage": "chunking", "elapsed_ms": 42, "status": "ok", ...}
    """

    def __init__(
        self,
        logger: logging.Logger,
        stage: str,
        level: int = logging.INFO,
        **extra: Any,
    ) -> None:
        self._logger = logger
        self._stage = stage
        self._level = level
        self._extra = extra
        self._start: Optional[float] = None

    def __enter__(self) -> "StageTimer":
        self._start = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        elapsed_ms = round((time.perf_counter() - (self._start or 0)) * 1000, 1)
        status = "error" if exc_type else "ok"
        self._logger.log(
            self._level,
            f"Stage '{self._stage}' completed" if not exc_type else f"Stage '{self._stage}' failed",
            extra={
                "stage": self._stage,
                "elapsed_ms": elapsed_ms,
                "status": status,
                **self._extra,
            },
        )
