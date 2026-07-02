"""Ensemble model wrappers."""

from betting_bot.models.ensemble.ensemble_manager import EnsembleManager
from betting_bot.models.ensemble.voting_ensemble import VotingEnsemble

__all__ = [
    "VotingEnsemble",
    "EnsembleManager",
]
