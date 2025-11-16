"""
Request ID tracking middleware for distributed tracing.
"""
import uuid
import contextvars
from typing import Any
from functools import wraps
import logging
import asyncio
import inspect

# Context variable for request ID (thread-safe and async-safe)
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default='')

logger = logging.getLogger(__name__)


class RequestIDFilter(logging.Filter):
    """Logging filter that adds request_id to all log records"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or 'no-request-id'  # type: ignore
        return True


def generate_request_id() -> str:
    """Generate unique request ID"""
    return str(uuid.uuid4())


def set_request_id(request_id: str | None = None) -> str:
    """
    Set request ID in context (generates if None).

    Args:
        request_id: Request ID to set, or None to generate new one

    Returns:
        The request ID that was set
    """
    if request_id is None:
        request_id = generate_request_id()
    request_id_var.set(request_id)
    return request_id


def get_request_id() -> str:
    """
    Get current request ID from context.

    Returns:
        Current request ID, or empty string if not set
    """
    return request_id_var.get()


def track_request(func):
    """
    Decorator to track request with unique ID.

    Works with both sync and async functions.
    Automatically generates request ID if not already set.
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        # Generate request ID if not already set
        request_id = get_request_id()
        if not request_id:
            request_id = set_request_id()

        logger.info(f"[{request_id}] Starting request: {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            logger.info(f"[{request_id}] Completed request: {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"[{request_id}] Failed request: {func.__name__} - {type(e).__name__}: {str(e)}")
            raise

    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        # Generate request ID if not already set
        request_id = get_request_id()
        if not request_id:
            request_id = set_request_id()

        logger.info(f"[{request_id}] Starting request: {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.info(f"[{request_id}] Completed request: {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"[{request_id}] Failed request: {func.__name__} - {type(e).__name__}: {str(e)}")
            raise

    # Return appropriate wrapper based on function type
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def configure_logging_with_request_id():
    """
    Configure logging to include request IDs in all log messages.

    Call this once at application startup.
    """
    # Create handler with request ID filter
    handler = logging.StreamHandler()
    handler.addFilter(RequestIDFilter())

    # Set format to include request_id
    formatter = logging.Formatter(
        '[%(request_id)s] %(levelname)s - %(name)s - %(message)s'
    )
    handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    logger.info("Request ID tracking configured")
