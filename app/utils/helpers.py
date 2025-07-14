import logging
import structlog
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from flask import jsonify, Response


def setup_logging(log_level: str = "INFO"):
    """Configure structured logging with JSON output."""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """Get configured structlog logger instance."""
    return structlog.get_logger(name)


class ApiResponse:
    """Standardized API response helper."""

    @staticmethod
    def success(
        data: Any = None, message: str = None, status_code: int = 200
    ) -> tuple[Response, int]:
        """Create success response with optional data and message."""
        response = {
            "success": True,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if data is not None:
            response["data"] = data
        if message:
            response["message"] = message

        return jsonify(response), status_code

    @staticmethod
    def error(
        message: str, details: Dict[str, Any] = None, status_code: int = 400
    ) -> tuple[Response, int]:
        """Create error response with message and optional details."""
        response = {
            "success": False,
            "error": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if details:
            response["details"] = details

        return jsonify(response), status_code


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    return dt.strftime(format_str) if dt else ""
