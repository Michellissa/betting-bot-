"""League and season repositories."""

from collections.abc import Sequence

from sqlalchemy import desc, select

from betting_bot.database.repositories.base import BaseRepository
from betting_bot.models.match import League, Season


class LeagueRepository(BaseRepository[League]):
    """Repository for league-specific queries."""

    def __init__(self, db) -> None:
        super().__init__(League, db)

    async def get_by_code(self, code: str) -> League | None:
        """Get a league by its code."""
        return await self.get_by(code=code)

    async def get_active_leagues(self) -> Sequence[League]:
        """Get all active leagues."""
        stmt = select(League).where(League.is_active == True).order_by(League.name)
        result = await self.db.execute(stmt)
        return result.scalars().all()


class SeasonRepository(BaseRepository[Season]):
    """Repository for season-specific queries."""

    def __init__(self, db) -> None:
        super().__init__(Season, db)

    async def get_current(self, league_id: int) -> Season | None:
        """Get the current season for a league."""
        return await self.get_by(league_id=league_id, is_current=True)

    async def get_by_league(self, league_id: int) -> Sequence[Season]:
        """Get all seasons for a league, ordered by most recent first."""
        stmt = (
            select(Season)
            .where(Season.league_id == league_id)
            .order_by(desc(Season.start_date))
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
