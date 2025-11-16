"""
Production-safe error handling utilities.
"""
import os
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Determine if running in production
IS_PRODUCTION = os.getenv("ENVIRONMENT", "production") == "production"


def sanitize_error_message(error: Exception, context: str = "") -> str:
    """
    Sanitize error message for safe display to users.

    In production: Return generic message, log detailed error
    In development: Return full error details

    Args:
        error: Exception that occurred
        context: Additional context about where error occurred

    Returns:
        Safe error message for user display
    """
    # Import here to avoid circular dependency
    from middleware.request_tracking import get_request_id

    # Log full error details server-side
    logger.error(f"Error in {context}: {type(error).__name__}: {str(error)}", exc_info=True)

    if IS_PRODUCTION:
        # Production: Return generic message with request ID for tracing
        request_id = get_request_id()
        if request_id:
            return f"An error occurred while processing your request. Error ID: {request_id}"
        else:
            return "An error occurred while processing your request."
    else:
        # Development: Return detailed message
        return f"{type(error).__name__}: {str(error)}"


def sanitize_sql_error(error: Exception, sql: str = "", params: list[Any] | None = None) -> str:
    """
    Sanitize SQL-related errors to prevent query exposure.

    Args:
        error: SQL exception
        sql: SQL query that failed (logged but not returned)
        params: Query parameters (logged but not returned)

    Returns:
        Safe error message
    """
    # Log SQL query server-side only (truncate long queries)
    if sql:
        truncated_sql = sql[:200] + "..." if len(sql) > 200 else sql
        logger.error(f"SQL query failed: {truncated_sql}")

    if params:
        logger.error(f"SQL params: {params}")

    logger.error(f"SQL error: {str(error)}", exc_info=True)

    if IS_PRODUCTION:
        return "Database query failed. Please check your input parameters."
    else:
        # In dev, show error type but NOT the full SQL query
        return f"Database error: {type(error).__name__}: {str(error)}"


def sanitize_validation_error(error: Exception) -> dict[str, Any]:
    """
    Sanitize Pydantic validation errors for user display.

    Args:
        error: Pydantic ValidationError

    Returns:
        User-friendly error dict
    """
    try:
        # Try to extract Pydantic error details
        if hasattr(error, 'errors'):
            errors = error.errors()  # type: ignore
            return {
                "error": "Invalid request parameters",
                "validation_errors": [
                    {
                        "field": ".".join(str(loc) for loc in err.get("loc", [])),
                        "message": err.get("msg", "Invalid value"),
                        "type": err.get("type", "unknown")
                    }
                    for err in errors
                ]
            }
    except Exception as e:
        logger.error(f"Error sanitizing validation error: {e}")

    # Fallback
    return {
        "error": "Invalid request parameters",
        "details": str(error) if not IS_PRODUCTION else "Please check your request format"
    }


def create_error_response(
    error: Exception,
    context: str = "",
    include_details: bool = False
) -> dict[str, Any]:
    """
    Create standardized error response dictionary.

    Args:
        error: Exception that occurred
        context: Context where error occurred
        include_details: Whether to include error details (forced False in production)

    Returns:
        Standardized error response dict
    """
    from middleware.request_tracking import get_request_id

    response: dict[str, Any] = {
        "error": sanitize_error_message(error, context),
        "request_id": get_request_id() or None
    }

    # Only include details in development or if explicitly requested
    if include_details and not IS_PRODUCTION:
        response["details"] = {
            "type": type(error).__name__,
            "message": str(error),
            "context": context
        }

    return response
