"""
App Configuration Module
========================
Handles FastAPI app configuration, CORS, middleware, and settings
Separated from main.py for better organization
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger("app.config")

# Version
VERSION = "10.0.0"


def create_app() -> FastAPI:
    """Factory function to create the FastAPI app"""
    app = FastAPI(
        title="Nexus Orchestrator",
        version=VERSION,
        description="Multi-tenant CRM with AI-powered sales automation",
    )

    # Configure CORS
    app = _configure_cors(app)

    # Add security middleware
    app = _configure_middleware(app)

    return app


def _configure_cors(app: FastAPI) -> FastAPI:
    """Configure CORS middleware"""
    _default_origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://crmventas-frontend.ugwrjq.easypanel.host",
    ]
    _env_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if _env_origins:
        _default_origins.extend(o.strip() for o in _env_origins.split(",") if o.strip())

    origins = list(dict.fromkeys(_default_origins))
    logger.info(f"CORS allow_origins: {origins}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    return app


def _configure_middleware(app: FastAPI) -> FastAPI:
    """Configure security middleware"""
    try:
        from core.security_middleware import SecurityHeadersMiddleware

        app.add_middleware(SecurityHeadersMiddleware)
        logger.info("✅ Security middleware added")
    except ImportError:
        logger.warning("⚠️ Security middleware not available")

    return app


# Settings helper
class Settings:
    """Application settings"""

    # Database
    POSTGRES_DSN = os.getenv("POSTGRES_DSN", "")

    # Auth
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

    # AI
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    # WhatsApp
    YCLOUD_API_KEY = os.getenv("YCLOUD_API_KEY", "")
    YCLOUD_WEBHOOK_SECRET = os.getenv("YCLOUD_WEBHOOK_SECRET", "")

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "")

    # Scheduled Tasks
    ENABLE_SCHEDULED_TASKS = (
        os.getenv("ENABLE_SCHEDULED_TASKS", "true").lower() == "true"
    )
    NOTIFICATION_INTERVAL = int(os.getenv("NOTIFICATION_CHECK_INTERVAL_MINUTES", "5"))
    METRICS_INTERVAL = int(os.getenv("METRICS_REFRESH_INTERVAL_MINUTES", "15"))
    CLEANUP_INTERVAL = int(os.getenv("CLEANUP_INTERVAL_HOURS", "1"))

    # Email
    IMAP_HOST = os.getenv("IMAP_HOST", "")

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


settings = Settings()
