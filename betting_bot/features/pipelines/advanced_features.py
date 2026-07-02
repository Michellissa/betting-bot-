"""Advanced features pipeline - possession, shots, defense, rest, league position.

Computes:
- home/away_possession_avg_5/10
- home/away_shots_avg_5/10
- home/away_shots_on_target_avg_5/10
- home/away_corners_avg_5/10
- home/away_fouls_avg_5
- home/away_yellow_cards_avg_5
- home_rest_days, away_rest_days
- home_league_position, away_league_position
- home_points, away_points, points_diff
- home_attack_strength, away_attack_strength
- home_defense_strength, away_defense_strength
"""

from collections.abc import Sequence
from datetime import timedelta
from typing import Any

from sqlalchemy import select, desc, or_

from betting_bot.core.constants import FeatureCategory
from betting_bot.features.pipelines.base_pipeline import BaseFeaturePipeline
from betting_bot.models.match import Match, TeamStats


class AdvancedFeaturesPipeline(BaseFeaturePipeline):
    """Computes advanced features from match statistics and league data."""

    def __init__(self, db) -> None:
        super().__init__(db)
        self.category = FeatureCategory.DERIVED

    @property
    def feature_names(self) -> list[str]:
        return [
            "home_possession_avg_5",
            "away_possession_avg_5",
            "home_possession_avg_10",
            "away_possession_avg_10",
            "home_shots_avg_5",
            "away_shots_avg_5",
            "home_shots_on_target_avg_5",
            "away_shots_on_target_avg_5",
            "home_shots_avg_10",
            "away_shots_avg_10",
            "home_shots_on_target_avg_10",
            "away_shots_on_target_avg_10",
            "home_corners_avg_5",
            "away_corners_avg_5",
            "home_corners_avg_10",
            "away_corners_avg_10",
            "home_fouls_avg_5",
            "away_fouls_avg_5",
            "home_yellow_cards_avg_5",
            "away_yellow_cards_avg_5",
            "home_rest_days",
            "away_rest_days",
            "home_league_position",
            "away_league_position",
            "home_points",
            "away_points",
            "points_diff",
            "home_attack_strength",
            "away_attack_strength",
            "home_defense_strength",
            "away_defense_strength",
        ]

    async def compute(self, match_id: int) -> dict[str, Any]:
        from betting_bot.database.repositories.match_repository import MatchRepository

        match_repo = MatchRepository(self.db)
        match = await match_repo.get_with_relations(match_id)

        if match is None:
            return {}

        features: dict[str, Any] = {}

        # Stats averages
        home_last_5 = await self._get_recent_matches(match.home_team_id, match.match_date, 5)
        home_last_10 = await self._get_recent_matches(match.home_team_id, match.match_date, 10)
        away_last_5 = await self._get_recent_matches(match.away_team_id, match.match_date, 5)
        away_last_10 = await self._get_recent_matches(match.away_team_id, match.match_date, 10)

        features.update(self._compute_stat_avgs(home_last_5, match.home_team_id, "home", 5))
        features.update(self._compute_stat_avgs(away_last_5, match.away_team_id, "away", 5))
        features.update(self._compute_stat_avgs(home_last_10, match.home_team_id, "home", 10))
        features.update(self._compute_stat_avgs(away_last_10, match.away_team_id, "away", 10))

        # Rest days
        features["home_rest_days"] = await self._compute_rest_days(
            match.home_team_id, match.match_date
        )
        features["away_rest_days"] = await self._compute_rest_days(
            match.away_team_id, match.match_date
        )

        # League position and points
        league_stats = await self._get_league_stats(match)
        features.update(league_stats)

        # Attack/defense strength
        features.update(self._compute_strength(features))

        return features

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

    def _compute_stat_avgs(
        self, matches: Sequence[Match], team_id: int, prefix: str, n: int
    ) -> dict[str, float]:
        """Compute averages for various match statistics."""
        default = {
            f"{prefix}_possession_avg_{n}": 0.0,
            f"{prefix}_shots_avg_{n}": 0.0,
            f"{prefix}_shots_on_target_avg_{n}": 0.0,
            f"{prefix}_corners_avg_{n}": 0.0,
        }
        if n <= 5:
            default.update({
                f"{prefix}_fouls_avg_{n}": 0.0,
                f"{prefix}_yellow_cards_avg_{n}": 0.0,
            })

        if not matches:
            return default

        possession = []
        shots = []
        shots_ot = []
        corners = []
        fouls = []
        yellows = []

        for m in matches:
            if m.home_team_id == team_id:
                if m.home_possession is not None:
                    possession.append(m.home_possession)
                shots.append(m.home_shots or 0)
                shots_ot.append(m.home_shots_on_target or 0)
                corners.append(m.home_corners or 0)
                fouls.append(m.home_fouls or 0)
                yellows.append(m.home_yellow_cards or 0)
            else:
                if m.away_possession is not None:
                    possession.append(m.away_possession)
                shots.append(m.away_shots or 0)
                shots_ot.append(m.away_shots_on_target or 0)
                corners.append(m.away_corners or 0)
                fouls.append(m.away_fouls or 0)
                yellows.append(m.away_yellow_cards or 0)

        result = {
            f"{prefix}_possession_avg_{n}": self.safe_avg(possession),
            f"{prefix}_shots_avg_{n}": self.safe_avg(shots),
            f"{prefix}_shots_on_target_avg_{n}": self.safe_avg(shots_ot),
            f"{prefix}_corners_avg_{n}": self.safe_avg(corners),
        }
        if n <= 5:
            result.update({
                f"{prefix}_fouls_avg_{n}": self.safe_avg(fouls),
                f"{prefix}_yellow_cards_avg_{n}": self.safe_avg(yellows),
            })

        return result

    async def _compute_rest_days(
        self, team_id: int, match_date: Any
    ) -> float:
        """Calculate rest days since last match."""
        stmt = (
            select(Match)
            .where(
                Match.is_finished == True,
                or_(
                    Match.home_team_id == team_id,
                    Match.away_team_id == team_id,
                ),
                Match.match_date < match_date,
            )
            .order_by(desc(Match.match_date))
            .limit(1)
        )
        result = await self.db.execute(stmt)
        last_match = result.scalar_one_or_none()

        if last_match is None or last_match.match_date is None:
            return 7.0

        delta = match_date - last_match.match_date
        if isinstance(delta, timedelta):
            return float(delta.days) + float(delta.seconds) / 86400.0
        return 7.0

    async def _get_league_stats(
        self, match: Match
    ) -> dict[str, Any]:
        """Get league position and points for both teams."""
        default = {
            "home_league_position": 0,
            "away_league_position": 0,
            "home_points": 0,
            "away_points": 0,
            "points_diff": 0,
        }

        if match.season_id is None:
            return default

        home_stmt = (
            select(TeamStats)
            .where(
                TeamStats.team_id == match.home_team_id,
                TeamStats.season_id == match.season_id,
                TeamStats.league_id == match.league_id,
            )
        )
        away_stmt = (
            select(TeamStats)
            .where(
                TeamStats.team_id == match.away_team_id,
                TeamStats.season_id == match.season_id,
                TeamStats.league_id == match.league_id,
            )
        )

        home_result = await self.db.execute(home_stmt)
        away_result = await self.db.execute(away_stmt)
        home_stats = home_result.scalar_one_or_none()
        away_stats = away_result.scalar_one_or_none()

        return {
            "home_league_position": home_stats.position if home_stats else 0,
            "away_league_position": away_stats.position if away_stats else 0,
            "home_points": home_stats.points if home_stats else 0,
            "away_points": away_stats.points if away_stats else 0,
            "points_diff": (home_stats.points if home_stats else 0)
                         - (away_stats.points if away_stats else 0),
        }

    def _compute_strength(
        self, features: dict[str, Any]
    ) -> dict[str, float]:
        """Compute attack and defense strength indicators."""
        return {
            "home_attack_strength": features.get("home_goals_scored_avg_5", 0.0)
                                   - features.get("away_goals_conceded_avg_5", 0.0),
            "away_attack_strength": features.get("away_goals_scored_avg_5", 0.0)
                                  - features.get("home_goals_conceded_avg_5", 0.0),
            "home_defense_strength": features.get("home_goals_conceded_avg_5", 0.0)
                                   - features.get("away_goals_scored_avg_5", 0.0),
            "away_defense_strength": features.get("away_goals_conceded_avg_5", 0.0)
                                  - features.get("home_goals_scored_avg_5", 0.0),
        }
