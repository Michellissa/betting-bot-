"""Database ORM models and ML model wrappers.

Classifier wrappers: betting_bot.models.classifiers
Ensemble wrappers:   betting_bot.models.ensemble
"""

from betting_bot.models.match import (
    League as LeagueModel,
    Team,
    Season,
    Match,
    Player,
    TeamStats,
    PlayerStats,
)
from betting_bot.models.odds import Odds, Bookmaker, OddsHistory
from betting_bot.models.prediction import Prediction, ModelPrediction, PredictionResult
from betting_bot.models.feature import FeatureDefinition, FeatureStore
from betting_bot.models.model_registry import ModelRegistry, ModelMetric

__all__ = [
    "LeagueModel",
    "Team",
    "Season",
    "Match",
    "Player",
    "TeamStats",
    "PlayerStats",
    "Odds",
    "Bookmaker",
    "OddsHistory",
    "Prediction",
    "ModelPrediction",
    "PredictionResult",
    "FeatureDefinition",
    "FeatureStore",
    "ModelRegistry",
    "ModelMetric",
]
