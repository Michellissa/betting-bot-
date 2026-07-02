"""Database session management - async and sync engines."""

from collections.abc import AsyncGenerator, Generator
from typing import Any

from loguru import logger
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from betting_bot.core.config import get_settings
from betting_bot.database.base import Base

_async_engine = None
_sync_engine = None
_async_session_factory = None
_sync_session_factory = None


def _engine_kwargs(url: str) -> dict:
    """Return engine kwargs, avoiding pool params for SQLite."""
    settings = get_settings()
    kwargs: dict = {"echo": settings.DB_ECHO}
    if "sqlite" not in url:
        kwargs["pool_size"] = settings.DB_POOL_SIZE
        kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    return kwargs


def get_async_engine() -> Any:
    """Create and return the async SQLAlchemy engine."""
    global _async_engine, _async_session_factory
    settings = get_settings()

    if _async_engine is None:
        _async_engine = create_async_engine(
            settings.database_url_async,
            **_engine_kwargs(settings.database_url_async),
        )
        _async_session_factory = async_sessionmaker(
            _async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_engine


def get_sync_engine() -> Any:
    """Create and return the sync SQLAlchemy engine."""
    global _sync_engine, _sync_session_factory
    settings = get_settings()

    if _sync_engine is None:
        _sync_engine = create_engine(
            settings.database_url_sync,
            **_engine_kwargs(settings.database_url_sync),
        )
        _sync_session_factory = sessionmaker(
            _sync_engine,
            class_=Session,
            expire_on_commit=False,
        )
    return _sync_engine


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield async database sessions."""
    get_async_engine()
    async with _async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session() -> Generator[Session, None, None]:
    """Yield sync database sessions."""
    get_sync_engine()
    with _sync_session_factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


async def init_db() -> None:
    """Create all database tables.

    Note: Models must be imported here to register them with Base.metadata
    before calling create_all.
    """
    # Import all model modules to register tables with Base.metadata
    from betting_bot.models import feature, match, model_registry, odds, prediction  # noqa: F401

    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


async def dispose_engine() -> None:
    """Dispose of the database engine."""
    global _async_engine, _sync_engine
    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
    if _sync_engine:
        _sync_engine.dispose()
        _sync_engine = None
        _sync_session_factory = None
    logger.info("Database engines disposed")
