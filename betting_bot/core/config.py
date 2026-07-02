"""Application settings via pydantic-settings (loads from .env)."""

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "BettingBot"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    LOG_FORMAT: str = "pretty"
    SECRET_KEY: str = "change-me-to-a-random-secret"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/betting_bot"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://user:password@localhost:5432/betting_bot"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # API Keys
    FOOTBALL_DATA_API_KEY: str = ""
    API_FOOTBALL_KEY: str = ""
    API_FOOTBALL_HOST: str = "v3.football.api-sports.io"
    ODDS_API_KEY: str = ""
    THESTATSAPI_KEY: str = ""
    SPORTMONKS_KEY: str = ""
    SPORTRADAR_KEY: str = ""
    WEATHER_API_KEY: str = ""

    # Model Training
    TRAINING_FEATURE_VERSION: str = "v1"
    MODEL_STORAGE_PATH: Path = Path("data/models")
    CACHE_ENABLED: bool = True
    CACHE_TTL: int = 3600
    REDIS_URL: str = "redis://localhost:6379/0"

    # Prediction
    MIN_CONFIDENCE_THRESHOLD: float = 0.50
    MIN_EV_THRESHOLD: float = 0.05
    KELLY_FRACTION: float = 0.25
    DEFAULT_STAKE: float = 100.0

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:8501",
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"Invalid log level: {v}. Allowed: {allowed}")
        return upper

    @property
    def is_production(self) -> bool:
        return not self.DEBUG

    @property
    def database_url_async(self) -> str:
        return self.DATABASE_URL

    @property
    def database_url_sync(self) -> str:
        if self.DATABASE_SYNC_URL:
            return self.DATABASE_SYNC_URL
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
