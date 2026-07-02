"""Form-based features pipeline.

Computes:
- home_form_last_5, away_form_last_5
- home_form_last_10, away_form_last_10
- home_points_last_5, away_points_last_5
- home_points_last_10, away_points_last_10
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import select, desc, or_

from betting_bot.core.constants import FeatureCategory, MatchResult
from betting_bot.features.pipelines.base_pipeline import BaseFeaturePipeline
from betting_bot.models.match import Match


class FormFeaturesPipeline(BaseFeaturePipeline):
    """Computes team form features from recent matches."""

    def __init__(self, db) -> None:
        super().__init__(db)
        self.category = FeatureCategory.FORM

    @property
    def feature_names(self) -> list[str]:
        return [
            "home_form_last_5",
            "away_form_last_5",
            "home_form_last_10",
            "away_form_last_10",
            "home_points_last_5",
            "away_points_last_5",
            "home_points_last_10",
            "away_points_last_10",
            "home_form_trend",
            "away_form_trend",
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

        home_form_5, home_points_5 = self._calculate_form(home_last_5, home_team_id)
        home_form_10, home_points_10 = self._calculate_form(home_last_10, home_team_id)
        away_form_5, away_points_5 = self._calculate_form(away_last_5, away_team_id)
        away_form_10, away_points_10 = self._calculate_form(away_last_10, away_team_id)

        return {
            "home_form_last_5": home_form_5,
            "away_form_last_5": away_form_5,
            "home_form_last_10": home_form_10,
            "away_form_last_10": away_form_10,
            "home_points_last_5": home_points_5,
            "away_points_last_5": away_points_5,
            "home_points_last_10": home_points_10,
            "away_points_last_10": away_points_10,
            "home_form_trend": home_form_10 - home_form_5 if home_last_10 else 0.0,
            "away_form_trend": away_form_10 - away_form_5 if away_last_10 else 0.0,
        }

    async def _get_recent_matches(
        self, team_id: int, before_date: Any, limit: int
    ) -> Sequence[Match]:
        """Get recent finished matches for a team before a given date."""
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

    def _calculate_form(
        self, matches: Sequence[Match], team_id: int
    ) -> tuple[float, float]:
        """Calculate form (win rate) and total points from matches.

        Form: 1.0 for win, 0.5 for draw, 0.0 for loss, averaged.
        Points: 3 for win, 1 for draw, 0 for loss.
        """
        if not matches:
            return 0.0, 0.0

        form_sum = 0.0
        points_sum = 0.0

        for m in matches:
            is_home = m.home_team_id == team_id
            if is_home:
                if m.result == MatchResult.HOME_WIN.value:
                    form_sum += 1.0
                    points_sum += 3.0
                elif m.result == MatchResult.DRAW.value:
                    form_sum += 0.5
                    points_sum += 1.0
            else:
                if m.result == MatchResult.AWAY_WIN.value:
                    form_sum += 1.0
                    points_sum += 3.0
                elif m.result == MatchResult.DRAW.value:
                    form_sum += 0.5
                    points_sum += 1.0

        return form_sum / len(matches), points_sum
