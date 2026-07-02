"""Head-to-head features pipeline.

Computes:
- h2h_home_wins, h2h_draws, h2h_away_wins
- h2h_home_goals_avg, h2h_away_goals_avg
- h2h_matches_played
- h2h_home_win_rate, h2h_away_win_rate
- h2h_over_2_5_rate, h2h_btts_rate
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select, or_, and_, desc

from betting_bot.core.constants import FeatureCategory, MatchResult
from betting_bot.features.pipelines.base_pipeline import BaseFeaturePipeline
from betting_bot.models.match import Match


class H2HFeaturesPipeline(BaseFeaturePipeline):
    """Computes head-to-head features between two teams."""

    def __init__(self, db) -> None:
        super().__init__(db)
        self.category = FeatureCategory.H2H

    @property
    def feature_names(self) -> list[str]:
        return [
            "h2h_home_wins",
            "h2h_draws",
            "h2h_away_wins",
            "h2h_home_goals_avg",
            "h2h_away_goals_avg",
            "h2h_matches_played",
            "h2h_home_win_rate",
            "h2h_away_win_rate",
            "h2h_over_2_5_rate",
            "h2h_btts_rate",
        ]

    async def compute(self, match_id: int) -> dict[str, Any]:
        from betting_bot.database.repositories.match_repository import MatchRepository

        match_repo = MatchRepository(self.db)
        match = await match_repo.get(match_id)

        if match is None:
            return {}

        h2h_matches = await self._get_h2h_matches(
            match.home_team_id, match.away_team_id, match.match_date
        )

        if not h2h_matches:
            return {
                "h2h_home_wins": 0,
                "h2h_draws": 0,
                "h2h_away_wins": 0,
                "h2h_home_goals_avg": 0.0,
                "h2h_away_goals_avg": 0.0,
                "h2h_matches_played": 0,
                "h2h_home_win_rate": 0.0,
                "h2h_away_win_rate": 0.0,
                "h2h_over_2_5_rate": 0.0,
                "h2h_btts_rate": 0.0,
            }

        home_wins = 0
        away_wins = 0
        draws = 0
        home_goals = []
        away_goals = []
        over_2_5 = 0
        btts = 0

        for m in h2h_matches:
            if m.home_goals is None or m.away_goals is None:
                continue

            if m.result == MatchResult.HOME_WIN.value:
                home_wins += 1
            elif m.result == MatchResult.AWAY_WIN.value:
                away_wins += 1
            else:
                draws += 1

            home_goals.append(m.home_goals)
            away_goals.append(m.away_goals)

            if m.home_goals + m.away_goals > 2.5:
                over_2_5 += 1
            if m.home_goals > 0 and m.away_goals > 0:
                btts += 1

        n = len(h2h_matches)

        return {
            "h2h_home_wins": home_wins,
            "h2h_draws": draws,
            "h2h_away_wins": away_wins,
            "h2h_home_goals_avg": self.safe_avg(home_goals),
            "h2h_away_goals_avg": self.safe_avg(away_goals),
            "h2h_matches_played": n,
            "h2h_home_win_rate": home_wins / n,
            "h2h_away_win_rate": away_wins / n,
            "h2h_over_2_5_rate": over_2_5 / n,
            "h2h_btts_rate": btts / n,
        }

    async def _get_h2h_matches(
        self, team1_id: int, team2_id: int, before_date: Any
    ) -> Sequence[Match]:
        """Get head-to-head matches between two teams."""
        stmt = (
            select(Match)
            .where(
                Match.is_finished == True,
                Match.match_date < before_date,
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
            .limit(20)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
