"""Confidence and value betting calculators."""

import numpy as np

from betting_bot.core.constants import ConfidenceLevel, RiskLevel


class ConfidenceCalculator:
    """Calculates confidence scores for predictions."""

    @staticmethod
    def from_probabilities(
        home_win: float, draw: float, away_win: float
    ) -> tuple[float, str]:
        """Calculate confidence from predicted probabilities.

        Higher confidence when there's a clear favorite (large spread).
        """
        probs = sorted([home_win, draw, away_win], reverse=True)
        spread = probs[0] - probs[1]
        confidence = float(np.clip(spread, 0.0, 1.0))
        level = ConfidenceLevel.from_score(confidence).value
        return confidence, level

    @staticmethod
    def from_model_agreement(
        model_predictions: list[dict[str, float]],
    ) -> tuple[float, str]:
        """Calculate confidence based on agreement between multiple models."""
        if not model_predictions:
            return 0.0, ConfidenceLevel.VERY_LOW.value

        home_probs = [p.get("home_win_probability", 0) for p in model_predictions]
        draw_probs = [p.get("draw_probability", 0) for p in model_predictions]
        away_probs = [p.get("away_win_probability", 0) for p in model_predictions]

        home_std = float(np.std(home_probs))
        draw_std = float(np.std(draw_probs))
        away_std = float(np.std(away_probs))

        avg_std = (home_std + draw_std + away_std) / 3.0
        confidence = float(np.clip(1.0 - avg_std * 2, 0.0, 1.0))
        level = ConfidenceLevel.from_score(confidence).value
        return confidence, level


class RiskCalculator:
    """Calculates risk scores for betting suggestions."""

    @staticmethod
    def from_probabilities(
        home_win: float, draw: float, away_win: float
    ) -> tuple[float, str]:
        """Calculate risk from probability distribution.

        Higher risk when probabilities are evenly distributed (uncertain match).
        """
        probs = np.array([home_win, draw, away_win])
        entropy = -np.sum(probs * np.log(probs + 1e-10)) / np.log(3)
        risk = float(np.clip(entropy, 0.0, 1.0))
        level = RiskLevel.from_value(risk).value
        return risk, level

    @staticmethod
    def expected_value(
        probability: float, odds: float
    ) -> float:
        """Calculate expected value for a bet.

        EV = (probability * odds) - 1

        Positive EV indicates a value bet.
        """
        return float(probability * odds - 1.0)

    @staticmethod
    def kelly_stake(
        probability: float,
        odds: float,
        bankroll: float,
        fraction: float = 0.25,
    ) -> float:
        """Calculate Kelly Criterion stake.

        f* = (p * (b + 1) - 1) / b
        where b = odds - 1, p = probability
        """
        b = odds - 1.0
        if b <= 0:
            return 0.0

        kelly = (probability * (b + 1) - 1) / b
        kelly = max(0.0, kelly)
        kelly = min(kelly, 0.1)

        return float(bankroll * kelly * fraction)


class ValueBetDetector:
    """Detects value betting opportunities."""

    def __init__(
        self,
        min_ev: float = 0.05,
        kelly_fraction: float = 0.25,
    ) -> None:
        self.min_ev = min_ev
        self.kelly_fraction = kelly_fraction

    def is_value_bet(
        self,
        model_probability: float,
        market_odds: float,
    ) -> bool:
        """Check if a bet has positive expected value."""
        ev = RiskCalculator.expected_value(model_probability, market_odds)
        return ev >= self.min_ev

    def get_value_rating(
        self,
        model_probability: float,
        market_odds: float,
    ) -> float:
        """Rating from 0-1 indicating strength of value opportunity."""
        ev = RiskCalculator.expected_value(model_probability, market_odds)
        if ev <= 0:
            return 0.0
        return float(np.clip(ev / 0.5, 0.0, 1.0))

    def suggest_stake(
        self,
        model_probability: float,
        market_odds: float,
        bankroll: float,
    ) -> float:
        """Suggest stake amount based on Kelly Criterion."""
        return RiskCalculator.kelly_stake(
            model_probability,
            market_odds,
            bankroll,
            self.kelly_fraction,
        )
