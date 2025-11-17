"""
Configuration management for Weight Loss Chat Agent.

This module provides centralized configuration management using Pydantic
for validation and type safety. All settings are loaded from environment
variables with sensible defaults and validation rules.

Configuration includes:
- API keys and credentials
- Database settings
- Telegram bot configuration
- Application settings and limits
- Logging configuration
"""

import os
import secrets
from typing import Optional, List
from pathlib import Path

from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings with environment variable loading and validation.

    Uses Pydantic BaseSettings for automatic environment variable binding
    with validation, type conversion, and default values.
    """

    # Application Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Database Configuration
    database_url: str = Field(default="sqlite:///weight_loss_app.db", env="DATABASE_URL")
    database_encrypt: bool = Field(default=False, env="DATABASE_ENCRYPT")
    database_key: Optional[str] = Field(default=None, env="DATABASE_KEY")

    # Telegram Bot Configuration
    telegram_bot_token: str = Field(..., env="TELEGRAM_BOT_TOKEN")
    telegram_admin_user_id: str = Field(..., env="TELEGRAM_ADMIN_USER_ID")
    telegram_webhook_url: Optional[str] = Field(default=None, env="TELEGRAM_WEBHOOK_URL")

    # Google Cloud Configuration
    google_cloud_project: str = Field(..., env="GOOGLE_CLOUD_PROJECT")
    google_cloud_location: str = Field(default="us-central1", env="GOOGLE_CLOUD_LOCATION")

    # Gemini API Configuration
    google_genai_api_key: str = Field(..., env="GOOGLE_GENAI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash-lite", env="GEMINI_MODEL")
    gemini_temperature: float = Field(default=0.7, env="GEMINI_TEMPERATURE")
    gemini_max_tokens: int = Field(default=2048, env="GEMINI_MAX_TOKENS")

    # Nutrition APIs
    usda_api_key: str = Field(default="demo", env="USDA_FDC_API_KEY")
    nutritionix_app_id: Optional[str] = Field(default=None, env="NUTRITIONIX_APP_ID")
    nutritionix_app_key: Optional[str] = Field(default=None, env="NUTRITIONIX_APP_KEY")

    # Application Limits and Timeouts
    max_batch_items: int = Field(default=10, env="MAX_BATCH_ITEMS")
    api_timeout_seconds: int = Field(default=30, env="API_TIMEOUT_SECONDS")
    bot_response_timeout: int = Field(default=3, env="BOT_RESPONSE_TIMEOUT")
    max_daily_logs: int = Field(default=20, env="MAX_DAILY_LOGS")

    # Session and Memory Configuration
    session_timeout_hours: int = Field(default=24, env="SESSION_TIMEOUT_HOURS")
    memory_window_days: int = Field(default=30, env="MEMORY_WINDOW_DAYS")

    # Nudge Scheduling
    nudge_enabled: bool = Field(default=True, env="NUDGE_ENABLED")
    nudge_morning_hour: int = Field(default=8, env="NUDGE_MORNING_HOUR")
    nudge_midday_hour: int = Field(default=12, env="NUDGE_MIDDAY_HOUR")
    nudge_evening_hour: int = Field(default=18, env="NUDGE_EVENING_HOUR")

    # Security and Privacy
    encryption_enabled: bool = Field(default=True, env="ENCRYPTION_ENABLED")
    log_sensitive_data: bool = Field(default=False, env="LOG_SENSITIVE_DATA")
    gdpr_deletion_enabled: bool = Field(default=True, env="GDPR_DELETION_ENABLED")

    # Development and Testing
    test_mode: bool = Field(default=False, env="TEST_MODE")
    mock_apis: bool = Field(default=False, env="MOCK_APIS")

    # File Paths
    log_file_path: str = Field(default="logs/bot.log", env="LOG_FILE_PATH")
    database_file_path: str = Field(default="weight_loss_app.db", env="DATABASE_FILE_PATH")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",  # Allow extra environment variables
    }

    @validator('telegram_bot_token')
    def validate_telegram_token(cls, v):
        """Validate Telegram bot token format."""
        if not v or len(v) < 45:  # Telegram tokens are typically 45+ characters
            raise ValueError('Invalid Telegram bot token format')
        return v

    @validator('telegram_admin_user_id')
    def validate_admin_user_id(cls, v):
        """Validate Telegram admin user ID is numeric."""
        try:
            int(v)
            return v
        except ValueError:
            raise ValueError('Telegram admin user ID must be numeric')

    @validator('google_genai_api_key')
    def validate_gemini_api_key(cls, v):
        """Validate Gemini API key format."""
        if not v or len(v) < 20:  # Gemini API keys are typically long
            raise ValueError('Invalid Gemini API key format')
        return v

    @validator('database_url')
    def validate_database_url(cls, v):
        """Validate database URL format."""
        if not v.startswith(('sqlite://', 'postgresql://', 'mysql://')):
            raise ValueError('Unsupported database URL scheme')
        return v

    @validator('log_level')
    def validate_log_level(cls, v):
        """Validate log level is supported."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {", ".join(valid_levels)}')
        return v.upper()

    @validator('gemini_temperature')
    def validate_temperature(cls, v):
        """Validate Gemini temperature is in valid range."""
        if not 0.0 <= v <= 2.0:
            raise ValueError('Gemini temperature must be between 0.0 and 2.0')
        return v

    @validator('max_batch_items')
    def validate_max_batch_items(cls, v):
        """Validate max batch items is reasonable."""
        if not 1 <= v <= 50:
            raise ValueError('Max batch items must be between 1 and 50')
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"

    @property
    def database_path(self) -> Path:
        """Get the absolute path to the database file."""
        if self.database_url.startswith('sqlite:///'):
            db_path = self.database_url.replace('sqlite:///', '')
            return Path(db_path).resolve()
        return Path(self.database_file_path).resolve()

    @property
    def log_path(self) -> Path:
        """Get the absolute path to the log file."""
        return Path(self.log_file_path).resolve()

    def get_database_key(self) -> Optional[str]:
        """Get database encryption key, generating if needed."""
        if not self.encryption_enabled:
            return None

        if self.database_key:
            return self.database_key

        # Generate a new key if encryption is enabled but no key provided
        # In production, this should be set explicitly
        if self.is_production:
            raise ValueError("Database encryption key must be provided in production")

        # Generate a random key for development
        key = secrets.token_hex(32)  # 256-bit key
        print(f"WARNING: Generated new database key: {key}")
        print("Set DATABASE_KEY environment variable to persist this key")
        return key

    def get_nudge_schedule(self) -> dict:
        """Get nudge scheduling configuration."""
        return {
            'morning': self.nudge_morning_hour,
            'midday': self.nudge_midday_hour,
            'evening': self.nudge_evening_hour,
            'enabled': self.nudge_enabled
        }

    def get_api_limits(self) -> dict:
        """Get API rate limiting configuration."""
        return {
            'max_daily_logs': self.max_daily_logs,
            'api_timeout': self.api_timeout_seconds,
            'bot_timeout': self.bot_response_timeout
        }


# Global settings instance
settings = Settings()

# Export settings and validation functions
__all__ = ['Settings', 'settings']