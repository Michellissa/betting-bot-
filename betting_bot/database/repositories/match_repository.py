"""Match repository with football-specific queries."""

from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.orm import joinedload

from betting_bot.database.repositories.base import BaseRepository
from betting_bot.models.match import League, Match, Team


class MatchRepository(BaseRepository[Match]):
    """Repository for match-specific queries."""

    def __init__(self, db) -> None:
        super().__init__(Match, db)

    async def get_with_relations(self, match_id: int) -> Match | None:
        """Get match with all related data loaded."""
        stmt = (
            select(Match)
            .options(
                joinedload(Match.home_team),
                joinedload(Match.away_team),
                joinedload(Match.league),
                joinedload(Match.season),
            )
            .where(Match.id == match_id)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalar_one_or_none()

    async def get_upcoming_matches(
        self,
        league_code: str | None = None,
        limit: int = 50,
    ) -> Sequence[Match]:
        """Get upcoming matches that haven't been played yet."""
        stmt = (
            select(Match)
            .options(
                joinedload(Match.home_team),
                joinedload(Match.away_team),
                joinedload(Match.league),
            )
            .where(
                Match.is_finished == False,
                Match.is_postponed == False,
                Match.match_date >= datetime.now(),
            )
            .order_by(Match.match_date)
        )
        if league_code:
            stmt = stmt.join(League).where(League.code == league_code)
        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return result.unique().scalars().all()

    async def get_recent_matches(
        self,
        team_id: int | None = None,
        league_id: int | None = None,
        limit: int = 10,
    ) -> Sequence[Match]:
        """Get most recent finished matches."""
        stmt = (
            select(Match)
            .options(
                joinedload(Match.home_team),
                joinedload(Match.away_team),
            )
            .where(Match.is_finished == True)
            .order_by(desc(Match.match_date))
        )
        if team_id:
            stmt = stmt.where(
                or_(Match.home_team_id == team_id, Match.away_team_id == team_id)
            )
        if league_id:
            stmt = stmt.where(Match.league_id == league_id)
        stmt = stmt.limit(limit)
        result = await self.db.execute(stmt)
        return result.unique().scalars().all()

    async def get_head_to_head(
        self,
        team1_id: int,
        team2_id: int,
        limit: int = 10,
    ) -> Sequence[Match]:
        """Get head-to-head matches between two teams."""
        stmt = (
            select(Match)
            .options(
                joinedload(Match.home_team),
                joinedload(Match.away_team),
            )
            .where(
                Match.is_finished == True,
                or_(
                    and_(
                        Match.home_team_id == team1_id,
                        Match.away_team_id == team2_id,
                    ),
                    and_(
                        Match.home_team_id == team2_id,
                        Match.away_team_id == team1_id,
                    ),
                ),
            )
            .order_by(desc(Match.match_date))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalars().all()

    async def get_team_matches_in_range(
        self,
        team_id: int,
        start_date: date,
        end_date: date,
    ) -> Sequence[Match]:
        """Get all matches for a team within a date range."""
        stmt = (
            select(Match)
            .options(
                joinedload(Match.home_team),
                joinedload(Match.away_team),
            )
            .where(
                or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
                Match.match_date >= start_date,
                Match.match_date <= end_date,
                Match.is_finished == True,
            )
            .order_by(Match.match_date)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalars().all()

    async def search_by_team_name(
        self,
        query: str,
        limit: int = 20,
    ) -> Sequence[Match]:
        """Search matches by home or away team name."""
        stmt = (
            select(Match)
            .options(
                joinedload(Match.home_team),
                joinedload(Match.away_team),
                joinedload(Match.league),
            )
            .join(Team, Match.home_team_id == Team.id)
            .where(Team.name.ilike(f"%{query}%"))
            .order_by(desc(Match.match_date))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.unique().scalars().all()


class TeamRepository(BaseRepository[Team]):
    """Repository for team-specific queries."""

    def __init__(self, db) -> None:
        super().__init__(Team, db)

    async def search_by_name(self, query: str, limit: int = 20) -> Sequence[Team]:
        """Search teams by name."""
        stmt = (
            select(Team)
            .where(Team.name.ilike(f"%{query}%"))
            .order_by(Team.name)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_league(self, league_id: int) -> Sequence[Team]:
        """Get all teams in a league."""
        stmt = select(Team).where(Team.league_id == league_id).order_by(Team.name)
        result = await self.db.execute(stmt)
        return result.scalars().all()


