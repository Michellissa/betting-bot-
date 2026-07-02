"""Elo-based features pipeline.

Computes:
- home_elo, away_elo
- elo_diff
- home_elo_home_advantage
- home_win_prob_elo
"""

from typing import Any

from sqlalchemy import select

from betting_bot.core.constants import FeatureCategory
from betting_bot.features.pipelines.base_pipeline import BaseFeaturePipeline
from betting_bot.models.match import Team, Match
from betting_bot.services.elo import EloRating


class EloFeaturesPipeline(BaseFeaturePipeline):
    """Computes Elo rating features."""

    def __init__(self, db) -> None:
        super().__init__(db)
        self.category = FeatureCategory.ELOC
        self.elo = EloRating()

    @property
    def feature_names(self) -> list[str]:
        return [
            "home_elo",
            "away_elo",
            "elo_diff",
            "home_elo_probability",
        ]

    async def compute(self, match_id: int) -> dict[str, Any]:
        from betting_bot.database.repositories.match_repository import MatchRepository

        match_repo = MatchRepository(self.db)
        match = await match_repo.get_with_relations(match_id)

        if match is None or match.home_team is None or match.away_team is None:
            return {}

        home_elo = match.home_team.elo_rating or 1500.0
        away_elo = match.away_team.elo_rating or 1500.0

        # Update Elo based on recent results before this match
        home_elo = await self._update_elo_for_recent(
            match.home_team_id, match.match_date, home_elo
        )
        away_elo = await self._update_elo_for_recent(
            match.away_team_id, match.match_date, away_elo
        )

        elo_diff = home_elo - away_elo
        prediction = self.elo.predict_match(home_elo, away_elo)

        return {
            "home_elo": home_elo,
            "away_elo": away_elo,
            "elo_diff": elo_diff,
            "home_elo_probability": prediction["home_win"],
        }

    async def _update_elo_for_recent(
        self, team_id: int, before_date: Any, current_elo: float
    ) -> float:
        """Recalculate Elo based on recent results."""
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
            if m.home_team_id == team_id:
                elo_result = self.elo.update(
                    elo, 1500.0, m.home_goals or 0, m.away_goals or 0
                )
                elo = elo_result.home_elo_after
            else:
                elo_result = self.elo.update(
                    1500.0, elo, m.home_goals or 0, m.away_goals or 0
                )
                elo = elo_result.away_elo_after

        return elo
