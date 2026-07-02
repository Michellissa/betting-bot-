"""FastAPI dependency injection."""

from betting_bot.api.dependencies.database import get_db, get_sync_db

__all__ = ["get_db", "get_sync_db"]
