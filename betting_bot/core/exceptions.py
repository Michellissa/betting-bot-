"""Custom exceptions for the betting bot application."""


class BettingBotError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.details = details or {}
        super().__init__(message)


class ConfigurationError(BettingBotError):
    """Raised when configuration is invalid or missing."""

    pass


class DatabaseError(BettingBotError):
    """Raised when a database operation fails."""

    pass


class DataError(BettingBotError):
    """Raised when data is invalid, missing, or corrupted."""

    pass


class APIError(BettingBotError):
    """Raised when an external API call fails."""

    def __init__(self, message: str, status_code: int | None = None, details: dict | None = None) -> None:
        self.status_code = status_code
        super().__init__(message, details)


class ModelError(BettingBotError):
    """Raised when a model operation fails (training, loading, inference)."""

    pass


class PredictionError(BettingBotError):
    """Raised when a prediction cannot be generated."""

    pass


class FeatureEngineeringError(BettingBotError):
    """Raised when feature engineering fails."""

    pass


class OddsError(BettingBotError):
    """Raised when odds data cannot be processed."""

    pass


class InsufficientDataError(BettingBotError):
    """Raised when there is not enough data for calculations."""

    pass
