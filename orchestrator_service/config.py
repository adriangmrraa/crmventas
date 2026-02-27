"""
Configuration settings for CRM Ventas Orchestrator
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    POSTGRES_DSN: str = os.getenv("POSTGRES_DSN", "postgresql://user:password@localhost:5432/crmventas")
    
    # Redis
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    
    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
    
    # CORS
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "*")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Scheduled Tasks
    ENABLE_SCHEDULED_TASKS: bool = os.getenv("ENABLE_SCHEDULED_TASKS", "false").lower() == "true"
    NOTIFICATION_CHECK_INTERVAL_MINUTES: int = int(os.getenv("NOTIFICATION_CHECK_INTERVAL_MINUTES", "5"))
    METRICS_REFRESH_INTERVAL_MINUTES: int = int(os.getenv("METRICS_REFRESH_INTERVAL_MINUTES", "15"))
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Meta Ads
    META_APP_ID: Optional[str] = os.getenv("META_APP_ID")
    META_APP_SECRET: Optional[str] = os.getenv("META_APP_SECRET")
    META_ACCESS_TOKEN: Optional[str] = os.getenv("META_ACCESS_TOKEN")
    
    # WhatsApp (YCloud)
    YCLOUD_API_KEY: Optional[str] = os.getenv("YCLOUD_API_KEY")
    YCLOUD_WEBHOOK_SECRET: Optional[str] = os.getenv("YCLOUD_WEBHOOK_SECRET")
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()