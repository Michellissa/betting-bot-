"""xG-based features pipeline.

Computes:
- home/away_xg_avg_5/10
- home/away_xga_avg_5/10
- home/away_xg_diff
- home/away_xg_overperformance
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select, desc, or_

from betting_bot.core.constants import FeatureCategory
from betting_bot.features.pipelines.base_pipeline import BaseFeaturePipeline
from betting_bot.models.match import Match


class XgFeaturesPipeline(BaseFeaturePipeline):
    """Computes expected goals features from recent matches."""

    def __init__(self, db) -> None:
        super().__init__(db)
        self.category = FeatureCategory.XG

    @property
    def feature_names(self) -> list[str]:
        return [
            "home_xg_avg_5",
            "away_xg_avg_5",
            "home_xga_avg_5",
            "away_xga_avg_5",
            "home_xg_avg_10",
            "away_xg_avg_10",
            "home_xga_avg_10",
            "away_xga_avg_10",
            "home_xg_diff_5",
            "away_xg_diff_5",
            "home_xg_diff_10",
            "away_xg_diff_10",
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
            **self._compute_xg_stats(home_last_5, home_team_id, "home", 5),
            **self._compute_xg_stats(away_last_5, away_team_id, "away", 5),
            **self._compute_xg_stats(home_last_10, home_team_id, "home", 10),
            **self._compute_xg_stats(away_last_10, away_team_id, "away", 10),
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

    def _compute_xg_stats(
        self, matches: Sequence[Match], team_id: int, prefix: str, n: int
    ) -> dict[str, float]:
        """Compute xG statistics for a set of matches."""
        if not matches:
            return {
                f"{prefix}_xg_avg_{n}": 0.0,
                f"{prefix}_xga_avg_{n}": 0.0,
                f"{prefix}_xg_diff_{n}": 0.0,
            }

        xg_values = []
        xga_values = []

        for m in matches:
            if m.home_team_id == team_id:
                xg = m.home_xg
                xga = m.home_xga
            else:
                xg = m.away_xg
                xga = m.away_xga

            if xg is not None:
                xg_values.append(xg)
            if xga is not None:
                xga_values.append(xga)

        xg_avg = self.safe_avg(xg_values)
        xga_avg = self.safe_avg(xga_values)

        return {
            f"{prefix}_xg_avg_{n}": xg_avg,
            f"{prefix}_xga_avg_{n}": xga_avg,
            f"{prefix}_xg_diff_{n}": xg_avg - xga_avg,
        }
