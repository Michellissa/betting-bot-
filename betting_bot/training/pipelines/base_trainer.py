"""Base trainer with common evaluation utilities."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

import numpy as np
import numpy.typing as npt
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit


@dataclass
class TrainResult:
    """Result of a single model training run."""

    model_name: str
    model_version: str
    feature_version: str
    training_date: datetime = field(default_factory=datetime.utcnow)
    training_duration_seconds: float = 0.0
    n_train_samples: int = 0
    n_features: int = 0
    target_variable: str = "result"

    # Cross-validation metrics
    cv_accuracy: list[float] = field(default_factory=list)
    cv_f1: list[float] = field(default_factory=list)
    cv_log_loss: list[float] = field(default_factory=list)
    cv_brier: list[float] = field(default_factory=list)
    cv_precision: list[float] = field(default_factory=list)
    cv_recall: list[float] = field(default_factory=list)
    cv_auc: list[float] = field(default_factory=list)

    # Test metrics (on genuine held-out data)
    test_accuracy: float = 0.0
    test_f1: float = 0.0
    test_log_loss: float = 0.0
    test_brier: float = 0.0
    test_precision: float = 0.0
    test_recall: float = 0.0
    test_auc: float = 0.0

    # Confusion matrix
    confusion_matrix: list[list[int]] = field(default_factory=list)

    # Feature importance
    feature_importance: dict[str, float] = field(default_factory=dict)
    top_features: list[tuple[str, float]] = field(default_factory=list)

    # Model params
    hyperparameters: dict = field(default_factory=dict)

    @property
    def avg_cv_accuracy(self) -> float:
        return float(np.mean(self.cv_accuracy)) if self.cv_accuracy else 0.0

    @property
    def avg_cv_f1(self) -> float:
        return float(np.mean(self.cv_f1)) if self.cv_f1 else 0.0

    @property
    def avg_cv_log_loss(self) -> float:
        return float(np.mean(self.cv_log_loss)) if self.cv_log_loss else 0.0

    @property
    def avg_cv_brier(self) -> float:
        return float(np.mean(self.cv_brier)) if self.cv_brier else 0.0


class BaseTrainer(ABC):
    """Abstract base trainer with common evaluation logic."""

    def __init__(self, random_state: int = 42, n_folds: int = 5) -> None:
        self.random_state = random_state
        self.n_folds = n_folds

    @staticmethod
    def compute_metrics(
        y_true: npt.NDArray[np.int64],
        y_pred: npt.NDArray[np.int64],
        y_proba: npt.NDArray[np.float64],
    ) -> dict[str, float]:
        """Compute standard classification metrics."""
        metrics = {
            "accuracy": accuracy_score(y_true, y_pred),
            "f1": f1_score(y_true, y_pred, average="weighted"),
            "precision": precision_score(y_true, y_pred, average="weighted", zero_division=0),
            "recall": recall_score(y_true, y_pred, average="weighted", zero_division=0),
            "log_loss": log_loss(y_true, y_proba),
        }
        try:
            if len(np.unique(y_true)) == 2:
                metrics["auc"] = roc_auc_score(y_true, y_proba[:, 1])
                metrics["brier"] = float(brier_score_loss(y_true, y_proba[:, 1]))
            else:
                metrics["auc"] = roc_auc_score(y_true, y_proba, multi_class="ovr")
                # Multiclass Brier score
                y_onehot = np.zeros_like(y_proba)
                y_onehot[np.arange(len(y_true)), y_true] = 1.0
                metrics["brier"] = float(np.mean(np.sum((y_proba - y_onehot) ** 2, axis=1)))
        except Exception:
            metrics["auc"] = 0.0
            metrics["brier"] = 1.0
        return metrics

    def cross_validate(
        self,
        model,
        X: npt.NDArray[np.float64],
        y: npt.NDArray[np.int64],
    ) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
        """Perform time-respecting cross-validation.

        Uses TimeSeriesSplit so that each fold's training set contains
        only matches occurring strictly before the validation set.
        Data must be sorted chronologically before calling this.
        """
        tscv = TimeSeriesSplit(n_splits=self.n_folds)
        fold_metrics = []

        for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
            X_train, X_val = X[train_idx], X[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]

            fold_model = model.__class__(**model.get_params())
            fold_model.fit(X_train, y_train)
            y_pred = fold_model.predict(X_val)
            y_proba = fold_model.predict_proba(X_val)

            metrics = self.compute_metrics(y_val, y_pred, y_proba)
            metrics["fold"] = fold
            fold_metrics.append(metrics)

        return fold_metrics

    @abstractmethod
    async def train(
        self,
        X: npt.NDArray[np.float64],
        y: npt.NDArray[np.int64],
        feature_names: list[str],
        model_config: dict | None = None,
    ) -> TrainResult: ...

    @abstractmethod
    async def train_and_register(
        self,
        X: npt.NDArray[np.float64],
        y: npt.NDArray[np.int64],
        feature_names: list[str],
        model_config: dict | None = None,
    ) -> TrainResult: ...
