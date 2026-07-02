"""Random Forest classifier wrapper."""

from pathlib import Path

import joblib
import numpy as np
import numpy.typing as npt
from sklearn.ensemble import RandomForestClassifier as SkLearnRF

from betting_bot.models.classifiers.base_classifier import BaseClassifier


class RandomForestClassifier(BaseClassifier):
    """Wrapper around sklearn RandomForestClassifier."""

    def __init__(
        self,
        n_estimators: int = 300,
        max_depth: int | None = 15,
        min_samples_split: int = 10,
        min_samples_leaf: int = 4,
        max_features: str = "sqrt",
        random_state: int = 42,
        class_weight: str | None = "balanced_subsample",
        n_jobs: int = -1,
        **kwargs,
    ) -> None:
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "min_samples_split": min_samples_split,
            "min_samples_leaf": min_samples_leaf,
            "max_features": max_features,
            "random_state": random_state,
            "class_weight": class_weight,
            "n_jobs": n_jobs,
            **kwargs,
        }
        self._model = SkLearnRF(**self.params)
        self._feature_names: list[str] = []

    def fit(
        self, X: npt.NDArray[np.float64] | np.ndarray, y: npt.NDArray[np.int64] | np.ndarray
    ) -> "RandomForestClassifier":
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
    def load(cls, path: str | Path) -> "RandomForestClassifier":
        data = joblib.load(path)
        instance = cls()
        instance._model = data["model"]
        instance._feature_names = data.get("feature_names", [])
        return instance

    @property
    def feature_importance(self) -> dict[str, float]:
        if self._model.feature_importances_ is None:
            return {}
        if self._feature_names:
            importances = self._model.feature_importances_
            return dict(zip(self._feature_names, map(float, importances), strict=False))
        return {
            f"feature_{i}": float(v) for i, v in enumerate(self._model.feature_importances_)
        }

    @property
    def model_type(self) -> str:
        return "sklearn"

    @property
    def model_class(self) -> str:
        return "RandomForestClassifier"

    def get_params(self) -> dict:
        return self.params

    def set_params(self, **params) -> None:
        self.params.update(params)
        self._model.set_params(**params)

    @property
    def classes_(self) -> list[int]:
        return list(self._model.classes_)
