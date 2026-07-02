"""Configuration loader with environment-specific overrides."""

from pathlib import Path
from typing import Any
from betting_bot.core.config import Settings, get_settings

from betting_bot.core.exceptions import ConfigurationError


def load_config() -> Settings:
    """Load and validate application configuration."""
    settings = get_settings()

    if settings.SECRET_KEY == "change-me-to-a-random-secret":
        raise ConfigurationError(
            "SECRET_KEY must be changed from the default value. "
            "Set it in your .env file or environment variables."
        )

    return settings


def get_db_config() -> dict[str, Any]:
    """Return database connection parameters."""
    settings = get_settings()
    return {
        "url": settings.database_url_async,
        "url_sync": settings.database_url_sync,
        "echo": settings.DB_ECHO,
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
    }


def get_api_config() -> dict[str, str]:
    """Return API key configuration for external data sources."""
    settings = get_settings()
    return {
        "football_data": settings.FOOTBALL_DATA_API_KEY,
        "api_football": settings.API_FOOTBALL_KEY,
        "odds_api": settings.ODDS_API_KEY,
        "weather": settings.WEATHER_API_KEY,
    }


def ensure_directories() -> None:
    """Ensure required directories exist."""
    settings = get_settings()
    directories = [
        settings.MODEL_STORAGE_PATH,
        Path("data/raw"),
        Path("data/processed"),
        Path("data/cache"),
        Path("logs"),
    ]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
