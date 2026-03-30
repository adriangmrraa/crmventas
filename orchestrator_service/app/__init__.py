"""
App Module - FastAPI Application Factory
=======================================
Provides the FastAPI app instance and configuration

Usage:
    from app import app
    # or
    from app.config import settings, create_app
"""

from .config import create_app, settings, VERSION

__all__ = ["app", "create_app", "settings", "VERSION"]

# Default app instance (for backward compatibility)
# Will be imported from main.py
app = None
