"""Goal-based features pipeline.

Computes:
- home/away_goals_scored_avg_5/10
- home/away_goals_conceded_avg_5/10
- home/away_goal_diff_avg_5/10
- home/away_scoring_streak
- home/away_clean_sheet_rate_5/10
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select, desc, or_

from betting_bot.core.constants import FeatureCategory
from betting_bot.features.pipelines.base_pipeline import BaseFeaturePipeline
from betting_bot.models.match import Match


class GoalFeaturesPipeline(BaseFeaturePipeline):
    """Computes goal-related features from recent matches."""

    def __init__(self, db) -> None:
        super().__init__(db)
        self.category = FeatureCategory.GOALS

    @property
    def feature_names(self) -> list[str]:
        return [
            "home_goals_scored_avg_5",
            "home_goals_conceded_avg_5",
            "away_goals_scored_avg_5",
            "away_goals_conceded_avg_5",
            "home_goals_scored_avg_10",
            "home_goals_conceded_avg_10",
            "away_goals_scored_avg_10",
            "away_goals_conceded_avg_10",
            "home_goal_diff_avg_5",
            "away_goal_diff_avg_5",
            "home_goal_diff_avg_10",
            "away_goal_diff_avg_10",
            "home_scoring_streak",
            "away_scoring_streak",
            "home_clean_sheet_rate_5",
            "away_clean_sheet_rate_5",
        ]

    async def compute(self, match_id: int) -> dict[str, Any]:
        from betting_bot.database.repositories.match_repository import MatchRepository

        match_repo = MatchRepository(self.db)
        match = await match_repo.get(match_id)

        if match is None:
            return {}

        home_team_id = match.home_team_id
        away_team_id = match.away_team_id
        match_date = match.match_date

        home_last_5 = await self._get_recent_matches(home_team_id, match_date, 5)
        home_last_10 = await self._get_recent_matches(home_team_id, match_date, 10)
        away_last_5 = await self._get_recent_matches(away_team_id, match_date, 5)
        away_last_10 = await self._get_recent_matches(away_team_id, match_date, 10)

        return {
            **self._compute_goal_stats(home_last_5, home_team_id, "home", 5),
            **self._compute_goal_stats(away_last_5, away_team_id, "away", 5),
            **self._compute_goal_stats(home_last_10, home_team_id, "home", 10),
            **self._compute_goal_stats(away_last_10, away_team_id, "away", 10),
        }

    async def _get_recent_matches(
        self, team_id: int, before_date: Any, limit: int
    ) -> Sequence[Match]:
        stmt = (
            select(Match)
            .where(
                Match.is_finished == True,
                or_(
                    Match.home_team_id == team_id,
                    Match.away_team_id == team_id,
                ),
                Match.match_date < before_date,
            )
            .order_by(desc(Match.match_date))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    def _compute_goal_stats(
        self, matches: Sequence[Match], team_id: int, prefix: str, n: int
    ) -> dict[str, float]:
        """Compute goal statistics for a set of matches."""
        if not matches:
            return {
                f"{prefix}_goals_scored_avg_{n}": 0.0,
                f"{prefix}_goals_conceded_avg_{n}": 0.0,
                f"{prefix}_goal_diff_avg_{n}": 0.0,
                f"{prefix}_scoring_streak": 0.0,
                f"{prefix}_clean_sheet_rate_{n}": 0.0,
            }

        goals_scored = []
        goals_conceded = []
        clean_sheets = 0

        for m in matches:
            if m.home_team_id == team_id:
                scored = m.home_goals or 0
                conceded = m.away_goals or 0
            else:
                scored = m.away_goals or 0
                conceded = m.home_goals or 0

            goals_scored.append(scored)
            goals_conceded.append(conceded)
            if conceded == 0:
                clean_sheets += 1

        # Scoring streak (consecutive matches with at least 1 goal)
        scoring_streak = 0
        for g in reversed(goals_scored):
            if g > 0:
                scoring_streak += 1
            else:
                break

        return {
            f"{prefix}_goals_scored_avg_{n}": self.safe_avg(goals_scored),
            f"{prefix}_goals_conceded_avg_{n}": self.safe_avg(goals_conceded),
            f"{prefix}_goal_diff_avg_{n}": self.safe_avg(goals_scored) - self.safe_avg(goals_conceded),
            f"{prefix}_scoring_streak": float(scoring_streak),
            f"{prefix}_clean_sheet_rate_{n}": clean_sheets / len(matches),
        }
