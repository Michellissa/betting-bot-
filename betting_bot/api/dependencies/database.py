"""Database session dependency injection for FastAPI routes."""

from collections.abc import AsyncGenerator, Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from betting_bot.database.session import get_async_session, get_sync_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session."""
    async for session in get_async_session():
        yield session


def get_sync_db() -> Generator[Session, None, None]:
    """Dependency that provides a sync database session."""
    for session in get_sync_session():
        yield session


AsyncDBSession = Annotated[AsyncSession, Depends(get_db)]
SyncDBSession = Annotated[Session, Depends(get_sync_db)]
