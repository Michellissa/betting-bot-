"""Base repository with common CRUD operations."""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic repository with common database operations."""

    def __init__(self, model: type[ModelT], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def create(self, **kwargs: Any) -> ModelT:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.flush()
        return instance

    async def get(self, id: int) -> ModelT | None:
        """Get a record by ID."""
        return await self.db.get(self.model, id)

    async def get_by(self, **kwargs: Any) -> ModelT | None:
        """Get first record matching criteria."""
        stmt = select(self.model).filter_by(**kwargs)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_many(
        self,
        skip: int = 0,
        limit: int = 100,
        order_by: Any | None = None,
        **filters: Any,
    ) -> tuple[Sequence[ModelT], int]:
        """Get multiple records with pagination."""
        count_stmt = select(self.model).filter_by(**filters)
        total_result = await self.db.execute(count_stmt)
        total = len(total_result.scalars().all())

        stmt = select(self.model).filter_by(**filters)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = result.scalars().all()

        return items, total

    async def update(self, id: int, **kwargs: Any) -> ModelT | None:
        """Update a record by ID."""
        instance = await self.get(id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.db.flush()
        return instance

    async def delete(self, id: int) -> bool:
        """Delete a record by ID."""
        stmt = sa_delete(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0

    async def exists(self, **kwargs: Any) -> bool:
        """Check if a record exists matching criteria."""
        stmt = select(self.model).filter_by(**kwargs)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
