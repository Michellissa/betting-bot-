"""Elo rating system for football teams."""

from dataclasses import dataclass

import numpy as np


@dataclass
class EloResult:
    """Result of an Elo rating update."""

    home_elo_before: float
    away_elo_before: float
    home_elo_after: float
    away_elo_after: float
    home_expected: float
    away_expected: float
    home_rating_change: float
    away_rating_change: float


class EloRating:
    """Elo rating system adapted for football predictions.

    Features:
    - Home advantage adjustment
    - Goal difference margin multiplier
    - K-factor adjustment based on match importance
    """

    def __init__(
        self,
        initial_rating: float = 1500.0,
        k_factor: float = 32.0,
        home_advantage: float = 100.0,
        goal_margin_factor: float = 1.0,
        regression_factor: float = 0.0,
    ) -> None:
        self.initial_rating = initial_rating
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.goal_margin_factor = goal_margin_factor
        self.regression_factor = regression_factor

    def expected_score(self, rating_a: float, rating_b: float) -> float:
        """Calculate expected score for team A against team B."""
        return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))

    def expected_scores(self, home_elo: float, away_elo: float) -> tuple[float, float]:
        """Calculate expected scores for both teams."""
        home_elo_adj = home_elo + self.home_advantage
        home_expected = self.expected_score(home_elo_adj, away_elo)
        away_expected = 1.0 - home_expected
        return home_expected, away_expected

    def goal_margin_multiplier(self, home_goals: int, away_goals: int) -> float:
        """Calculate multiplier based on goal difference margin."""
        goal_diff = abs(home_goals - away_goals)
        if goal_diff == 0:
            return 1.0
        return np.log(max(goal_diff, 1) + 1.0) * self.goal_margin_factor

    def update(
        self,
        home_elo: float,
        away_elo: float,
        home_goals: int,
        away_goals: int,
        is_neutral: bool = False,
    ) -> EloResult:
        """Update Elo ratings based on match result.

        Args:
            home_elo: Home team's current Elo rating.
            away_elo: Away team's current Elo rating.
            home_goals: Goals scored by home team.
            away_goals: Goals scored by away team.
            is_neutral: Whether match is at neutral venue.

        Returns:
            EloResult with before/after ratings and changes.
        """
        home_advantage = 0.0 if is_neutral else self.home_advantage
        home_elo_adj = home_elo + home_advantage

        home_expected = self.expected_score(home_elo_adj, away_elo)
        away_expected = 1.0 - home_expected

        if home_goals > away_goals:
            home_actual, away_actual = 1.0, 0.0
        elif home_goals < away_goals:
            home_actual, away_actual = 0.0, 1.0
        else:
            home_actual, away_actual = 0.5, 0.5

        margin_mult = self.goal_margin_multiplier(home_goals, away_goals)
        k = self.k_factor * margin_mult

        home_change = k * (home_actual - home_expected)
        away_change = k * (away_actual - away_expected)

        home_elo_new = home_elo + home_change
        away_elo_new = away_elo + away_change

        return EloResult(
            home_elo_before=home_elo,
            away_elo_before=away_elo,
            home_elo_after=home_elo_new,
            away_elo_after=away_elo_new,
            home_expected=home_expected,
            away_expected=away_expected,
            home_rating_change=home_change,
            away_rating_change=away_change,
        )

    def predict_match(self, home_elo: float, away_elo: float, is_neutral: bool = False) -> dict:
        """Predict match outcome probabilities from Elo ratings.

        Returns:
            Dict with home_win, draw, away_win probabilities.
        """
        home_adv = 0.0 if is_neutral else self.home_advantage
        home_expected = self.expected_score(home_elo + home_adv, away_elo)

        draw_prob = self._estimate_draw_probability(home_expected)
        home_win_prob = home_expected * (1.0 - draw_prob)
        away_win_prob = (1.0 - home_expected) * (1.0 - draw_prob)
        total = home_win_prob + draw_prob + away_win_prob

        return {
            "home_win": home_win_prob / total,
            "draw": draw_prob / total,
            "away_win": away_win_prob / total,
        }

    def _estimate_draw_probability(self, expected_home: float) -> float:
        """Estimate draw probability from expected score.

        Draws are more likely when teams are evenly matched.
        """
        imbalance = abs(expected_home - 0.5) * 2
        draw_prob = 0.28 * (1.0 - imbalance)
        return max(0.1, min(0.4, draw_prob))

    def apply_regression(self, elo: float, regression_periods: int = 1) -> float:
        """Apply mean regression toward initial rating."""
        if self.regression_factor <= 0 or regression_periods <= 0:
            return elo
        regression = (self.initial_rating - elo) * self.regression_factor * regression_periods
        return elo + regression
