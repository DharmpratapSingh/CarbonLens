"""
Centralized configuration management for ClimateGPT.
All environment variables and configurable parameters in one place.
"""
import os
import logging

logger = logging.getLogger(__name__)


class Config:
    """Application configuration loaded from environment variables"""

    # ========================================================================
    # ENVIRONMENT
    # ========================================================================
    ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
    IS_PRODUCTION = ENVIRONMENT == "production"
    IS_DEVELOPMENT = ENVIRONMENT == "development"

    # ========================================================================
    # DATABASE CONFIGURATION
    # ========================================================================
    DB_PATH = os.getenv("DB_PATH", "data/warehouse/climategpt.duckdb")
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_CONNECTIONS = int(os.getenv("DB_MAX_CONNECTIONS", "20"))

    # ========================================================================
    # LLM CONFIGURATION
    # ========================================================================
    LLM_CONCURRENCY_LIMIT = int(os.getenv("LLM_CONCURRENCY_LIMIT", "10"))
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    MODEL = os.getenv("MODEL", "/cache/climategpt_8b_test")

    # ========================================================================
    # RATE LIMITING
    # ========================================================================
    RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "100"))
    RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

    # ========================================================================
    # CORS CONFIGURATION
    # ========================================================================
    ALLOWED_ORIGINS_ENV = os.getenv("ALLOWED_ORIGINS")
    if not ALLOWED_ORIGINS_ENV:
        if IS_DEVELOPMENT:
            ALLOWED_ORIGINS = ["http://localhost:8501", "http://localhost:3000"]
        else:
            # Production requires explicit CORS configuration
            ALLOWED_ORIGINS = []
    else:
        ALLOWED_ORIGINS = [origin.strip() for origin in ALLOWED_ORIGINS_ENV.split(",")]

    # ========================================================================
    # CACHE CONFIGURATION
    # ========================================================================
    CACHE_SIZE = int(os.getenv("CACHE_SIZE", "1000"))
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))

    # ========================================================================
    # SERVER CONFIGURATION
    # ========================================================================
    HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")
    HTTP_PORT = int(os.getenv("HTTP_PORT", "8010"))

    # ========================================================================
    # VALIDATION
    # ========================================================================
    @classmethod
    def validate(cls):
        """Validate configuration and log warnings/errors"""

        # Validate database pool size
        if cls.DB_POOL_SIZE < 1:
            raise ValueError("DB_POOL_SIZE must be >= 1")
        if cls.DB_POOL_SIZE > 100:
            logger.warning(f"DB_POOL_SIZE={cls.DB_POOL_SIZE} is very high, may cause resource issues")

        # Validate LLM concurrency
        if cls.LLM_CONCURRENCY_LIMIT < 1:
            raise ValueError("LLM_CONCURRENCY_LIMIT must be >= 1")
        if cls.LLM_CONCURRENCY_LIMIT > 50:
            logger.warning(f"LLM_CONCURRENCY_LIMIT={cls.LLM_CONCURRENCY_LIMIT} is very high")

        # Validate API key
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        if ":" not in cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY must be in format 'username:password'")

        # Validate CORS in production
        if cls.IS_PRODUCTION and not cls.ALLOWED_ORIGINS:
            raise ValueError(
                "ALLOWED_ORIGINS environment variable is required in production. "
                "Set it to a comma-separated list of allowed origins."
            )

        # Log configuration
        logger.info(f"Environment: {cls.ENVIRONMENT}")
        logger.info(f"Database pool size: {cls.DB_POOL_SIZE}")
        logger.info(f"LLM concurrency limit: {cls.LLM_CONCURRENCY_LIMIT}")
        logger.info(f"Rate limiting: {cls.RATE_LIMIT_MAX_REQUESTS} requests per {cls.RATE_LIMIT_WINDOW_SECONDS}s")
        logger.info(f"Cache: {cls.CACHE_SIZE} entries, TTL {cls.CACHE_TTL_SECONDS}s")
        logger.info(f"CORS origins: {cls.ALLOWED_ORIGINS}")

    @classmethod
    def get_user_pass(cls) -> tuple[str, str]:
        """Extract username and password from API key"""
        if ":" in cls.OPENAI_API_KEY:
            parts = cls.OPENAI_API_KEY.split(":", 1)
            return parts[0], parts[1]
        raise ValueError("OPENAI_API_KEY must contain ':' separator")


# Initialize and validate configuration on import
try:
    Config.validate()
except Exception as e:
    logger.error(f"Configuration validation failed: {e}")
    # Re-raise in production, allow dev to continue with warnings
    if Config.IS_PRODUCTION:
        raise
