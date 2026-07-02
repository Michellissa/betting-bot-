"""Logistic Regression classifier wrapper."""

from pathlib import Path

import joblib
import numpy as np
import numpy.typing as npt
from sklearn.linear_model import LogisticRegression as SkLearnLR

from betting_bot.models.classifiers.base_classifier import BaseClassifier


class LogisticRegressionClassifier(BaseClassifier):
    """Wrapper around sklearn LogisticRegression."""

    def __init__(
        self,
        C: float = 1.0,
        penalty: str = "l2",
        solver: str = "lbfgs",
        max_iter: int = 1000,
        random_state: int = 42,
        class_weight: str | None = "balanced",
        **kwargs,
    ) -> None:
        self.params = {
            "C": C,
            "penalty": penalty,
            "solver": solver,
            "max_iter": max_iter,
            "random_state": random_state,
            "class_weight": class_weight,
            **kwargs,
        }
        self._model = SkLearnLR(**self.params)
        self._feature_names: list[str] = []

    def fit(
        self, X: npt.NDArray[np.float64] | np.ndarray, y: npt.NDArray[np.int64] | np.ndarray
    ) -> "LogisticRegressionClassifier":
        self._model.fit(X, y)
        return self

    def predict(self, X: npt.NDArray[np.float64] | np.ndarray) -> npt.NDArray[np.int64]:
        return self._model.predict(X)

    def predict_proba(
        self, X: npt.NDArray[np.float64] | np.ndarray
    ) -> npt.NDArray[np.float64]:
        return self._model.predict_proba(X)

    def save(self, path: str | Path) -> None:
        joblib.dump({"model": self._model, "feature_names": self._feature_names}, path)

    @classmethod
    def load(cls, path: str | Path) -> "LogisticRegressionClassifier":
        data = joblib.load(path)
        instance = cls()
        instance._model = data["model"]
        instance._feature_names = data.get("feature_names", [])
        return instance

    @property
    def feature_importance(self) -> dict[str, float]:
        if self._model.coef_ is None:
            return {}
        coef = self._model.coef_[0]
        if self._feature_names:
            return dict(zip(self._feature_names, map(float, np.abs(coef)), strict=False))
        return {f"feature_{i}": float(abs(c)) for i, c in enumerate(coef)}

    @property
    def model_type(self) -> str:
        return "sklearn"

    @property
    def model_class(self) -> str:
        return "LogisticRegression"

    def get_params(self) -> dict:
        return self.params

    def set_params(self, **params) -> None:
        self.params.update(params)
        self._model.set_params(**params)

    @property
    def classes_(self) -> list[int]:
        return list(self._model.classes_)
