"""Optuna-based hyperparameter optimization."""

from collections.abc import Callable
from typing import Any

import numpy as np
import numpy.typing as npt
import optuna
from loguru import logger
from sklearn.metrics import log_loss
from sklearn.model_selection import TimeSeriesSplit


class OptunaOptimizer:
    """Hyperparameter optimization using Optuna with cross-validation."""

    def __init__(
        self,
        model_class: type,
        search_space_fn: Callable,
        n_trials: int = 50,
        cv_folds: int = 5,
        random_state: int = 42,
        direction: str = "minimize",
        study_name: str | None = None,
    ) -> None:
        self.model_class = model_class
        self.search_space_fn = search_space_fn
        self.n_trials = n_trials
        self.cv_folds = cv_folds
        self.random_state = random_state
        self.direction = direction
        self.study_name = study_name
        self.study: optuna.Study | None = None

    def objective(self, X: npt.NDArray[np.float64], y: npt.NDArray[np.int64]) -> Callable:
        """Create the Optuna objective function."""

        def _objective(trial: optuna.Trial) -> float:
            params = self.search_space_fn(trial)

            self.model_class(random_state=self.random_state, **params)

            tscv = TimeSeriesSplit(n_splits=self.cv_folds)

            losses = []
            for train_idx, val_idx in tscv.split(X):
                X_train, X_val = X[train_idx], X[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]

                try:
                    fold_model = self.model_class(random_state=self.random_state, **params)
                    fold_model.fit(X_train, y_train)
                    y_proba = fold_model.predict_proba(X_val)
                    loss = log_loss(y_val, y_proba)
                    losses.append(loss)
                except Exception as e:
                    logger.warning(f"Trial {trial.number} failed: {e}")
                    return float("inf")

            return float(np.mean(losses))

        return _objective

    def optimize(
        self,
        X: npt.NDArray[np.float64],
        y: npt.NDArray[np.int64],
    ) -> dict[str, Any]:
        """Run hyperparameter optimization."""
        sampler = optuna.samplers.TPESampler(seed=self.random_state)
        pruner = optuna.pruners.MedianPruner()

        self.study = optuna.create_study(
            study_name=self.study_name,
            direction=self.direction,
            sampler=sampler,
            pruner=pruner,
        )

        objective_fn = self.objective(X, y)

        self.study.optimize(
            objective_fn,
            n_trials=self.n_trials,
            show_progress_bar=True,
        )

        best_params = self.study.best_params
        best_value = self.study.best_value

        logger.info(
            f"Optimization completed. Best log-loss: {best_value:.4f}\n"
            f"Best params: {best_params}"
        )
        return best_params

    def get_trials_dataframe(self):
        """Return study trials as a DataFrame."""
        if self.study is None:
            return None

        import pandas as pd

        records = []
        for trial in self.study.trials:
            record = {
                "number": trial.number,
                "value": trial.value,
                "state": trial.state.name,
                "datetime_start": trial.datetime_start,
                "datetime_complete": trial.datetime_complete,
                **trial.params,
            }
            records.append(record)
        return pd.DataFrame(records)
