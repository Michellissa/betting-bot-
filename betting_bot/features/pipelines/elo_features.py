"""Elo-based features pipeline.

Computes:
- home_elo, away_elo
- elo_diff
- home_elo_home_advantage
- home_win_prob_elo
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from betting_bot.core.constants import FeatureCategory
from betting_bot.features.pipelines.base_pipeline import BaseFeaturePipeline
from betting_bot.models.match import Team, Match, League
from betting_bot.services.elo import EloRating


class EloFeaturesPipeline(BaseFeaturePipeline):
    """Computes Elo rating features.

    Uses persistent ``Team.elo_rating`` values (pre-computed by
    ``scripts/compute_elo_ratings.py``) as the starting point and
    applies actual opponent Elo ratings for each recent match.

    For international competitions (country = "International") the
    home-venue bonus is suppressed (neutral site).
    """

    def __init__(self, db) -> None:
        super().__init__(db)
        self.category = FeatureCategory.ELOC
        self.elo = EloRating()

    # Cache set of international league IDs to avoid repeated DB lookups
    _international_league_ids: set[int] | None = None

    @property
    def feature_names(self) -> list[str]:
        return [
            "home_elo",
            "away_elo",
            "elo_diff",
            "home_elo_probability",
        ]

    async def _is_international_league(self, league_id: int | None) -> bool:
        """Check if a league is an international competition (neutral venue)."""
        if league_id is None:
            return False
        if EloFeaturesPipeline._international_league_ids is None:
            result = await self.db.execute(
                select(League.id).where(
                    League.country == "International",
                    League.is_active,
                )
            )
            EloFeaturesPipeline._international_league_ids = {row[0] for row in result.all()}
        return league_id in EloFeaturesPipeline._international_league_ids

    async def compute(self, match_id: int) -> dict[str, Any]:
        from betting_bot.database.repositories.match_repository import MatchRepository

        match_repo = MatchRepository(self.db)
        match = await match_repo.get_with_relations(match_id)

        if match is None or match.home_team is None or match.away_team is None:
            return {}

        home_elo = match.home_team.elo_rating or 1500.0
        away_elo = match.away_team.elo_rating or 1500.0

        # Determine if this is a neutral-venue international match
        is_neutral = await self._is_international_league(match.league_id)

        # Update Elo based on recent results before this match
        home_elo = await self._update_elo_for_recent(
            match.home_team_id, match.match_date, home_elo, is_neutral
        )
        away_elo = await self._update_elo_for_recent(
            match.away_team_id, match.match_date, away_elo, is_neutral
        )

        elo_diff = home_elo - away_elo
        prediction = self.elo.predict_match(home_elo, away_elo, is_neutral=is_neutral)

        return {
            "home_elo": home_elo,
            "away_elo": away_elo,
            "elo_diff": elo_diff,
            "home_elo_probability": prediction["home_win"],
        }

    async def _update_elo_for_recent(
        self, team_id: int, before_date: Any, current_elo: float,
        is_neutral: bool = False,
    ) -> float:
        """Recalculate Elo from scratch using last 20 matches.

        Uses actual opponent stored Elo ratings (from batch computation)
        instead of assuming 1500 for every opponent.

        For each recent match we check the match's own league to determine
        whether it was a neutral-venue international fixture.
        """
        from sqlalchemy import desc, or_

        stmt = (
            select(Match)
            .where(
                Match.is_finished == True,
                or_(
                    Match.home_team_id == team_id,
                    Match.away_team_id == team_id,
                ),
                Match.match_date < before_date,
                Match.home_goals.isnot(None),
                Match.away_goals.isnot(None),
            )
            .order_by(desc(Match.match_date))
            .limit(20)
        )
        result = await self.db.execute(stmt)
        recent_matches = result.scalars().all()

        elo = 1500.0
        for m in reversed(list(recent_matches)):
            is_home = m.home_team_id == team_id
            opp_team_id = m.away_team_id if is_home else m.home_team_id
            opp_team = await self.db.get(Team, opp_team_id)
            opponent_elo = opp_team.elo_rating or 1500.0 if opp_team else 1500.0

            # Check if this specific recent match was neutral venue
            match_is_neutral = is_neutral
            if not match_is_neutral and m.league_id:
                match_is_neutral = await self._is_international_league(m.league_id)

            if is_home:
                elo_result = self.elo.update(
                    elo, opponent_elo, m.home_goals or 0, m.away_goals or 0,
                    is_neutral=match_is_neutral,
                )
                elo = elo_result.home_elo_after
            else:
                elo_result = self.elo.update(
                    opponent_elo, elo, m.home_goals or 0, m.away_goals or 0,
                    is_neutral=match_is_neutral,
                )
                elo = elo_result.away_elo_after

        return elo
