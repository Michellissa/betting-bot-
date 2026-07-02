"""Odds and bookmaker repositories."""

from collections.abc import Sequence

from sqlalchemy import desc, select

from betting_bot.database.repositories.base import BaseRepository
from betting_bot.models.odds import Bookmaker, Odds, OddsHistory


class BookmakerRepository(BaseRepository[Bookmaker]):
    """Repository for bookmaker-specific queries."""

    def __init__(self, db) -> None:
        super().__init__(Bookmaker, db)

    async def get_by_name(self, name: str) -> Bookmaker | None:
        """Get a bookmaker by name."""
        return await self.get_by(name=name)

    async def get_active_bookmakers(self) -> Sequence[Bookmaker]:
        """Get all active bookmakers."""
        stmt = select(Bookmaker).where(Bookmaker.is_active == True).order_by(Bookmaker.name)
        result = await self.db.execute(stmt)
        return result.scalars().all()


class OddsRepository(BaseRepository[Odds]):
    """Repository for odds-specific queries."""

    def __init__(self, db) -> None:
        super().__init__(Odds, db)

    async def get_for_match(self, match_id: int) -> Sequence[Odds]:
        """Get all odds for a specific match."""
        stmt = select(Odds).where(Odds.match_id == match_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_latest_for_match(self, match_id: int) -> Odds | None:
        """Get the most recent odds for a match."""
        stmt = (
            select(Odds)
            .where(Odds.match_id == match_id)
            .order_by(desc(Odds.odds_timestamp))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_best_odds_for_match(self, match_id: int) -> dict:
        """Get the best (highest) odds across all bookmakers for a match."""
        odds_list = await self.get_for_match(match_id)
        if not odds_list:
            return {}

        best = {}
        for field in [
            "home_odds", "draw_odds", "away_odds",
            "over_2_5_odds", "under_2_5_odds",
            "btts_yes_odds", "btts_no_odds",
        ]:
            values = [getattr(o, field) for o in odds_list if getattr(o, field) is not None]
            if values:
                best[field] = max(values)
        return best


class OddsHistoryRepository(BaseRepository[OddsHistory]):
    """Repository for odds history queries."""

    def __init__(self, db) -> None:
        super().__init__(OddsHistory, db)

    async def get_for_match(
        self,
        match_id: int,
        bookmaker_id: int | None = None,
        limit: int = 100,
    ) -> Sequence[OddsHistory]:
        """Get odds history for a match, optionally filtered by bookmaker."""
        stmt = (
            select(OddsHistory)
            .where(OddsHistory.match_id == match_id)
            .order_by(desc(OddsHistory.recorded_at))
            .limit(limit)
        )
        if bookmaker_id is not None:
            stmt = stmt.where(OddsHistory.bookmaker_id == bookmaker_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()
