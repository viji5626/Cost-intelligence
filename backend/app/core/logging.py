"""
Structured Logging and Request Tracing Module
Separates system application logs from compliance audit logs.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON for easy parsing and log minimization."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        # Include request tracing if present
        if hasattr(record, "request_id"):
            log_obj["request_id"] = getattr(record, "request_id")
        if hasattr(record, "user_id"):
            log_obj["user_id"] = getattr(record, "user_id")
        if hasattr(record, "audit_metadata"):
            log_obj["audit_metadata"] = getattr(record, "audit_metadata")

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)


def setup_logging(log_level: str = "INFO") -> None:
    """Configures root application logger and audit logger."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clean existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(StructuredJsonFormatter())
    root_logger.addHandler(console_handler)

    # Silence chatty third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


logger = logging.getLogger("hero.app")
audit_logger = logging.getLogger("hero.audit")
