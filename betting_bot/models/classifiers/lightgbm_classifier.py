"""LightGBM classifier wrapper."""

from pathlib import Path

import joblib
import numpy as np
import numpy.typing as npt

from betting_bot.models.classifiers.base_classifier import BaseClassifier


class LightGBMClassifier(BaseClassifier):
    """Wrapper around LGBMClassifier."""

    def __init__(
        self,
        n_estimators: int = 500,
        max_depth: int = -1,
        num_leaves: int = 63,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        min_child_samples: int = 20,
        reg_alpha: float = 0.1,
        reg_lambda: float = 0.1,
        random_state: int = 42,
        n_jobs: int = -1,
        **kwargs,
    ) -> None:
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "num_leaves": num_leaves,
            "learning_rate": learning_rate,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "min_child_samples": min_child_samples,
            "reg_alpha": reg_alpha,
            "reg_lambda": reg_lambda,
            "random_state": random_state,
            "n_jobs": n_jobs,
            "verbose": -1,
            **kwargs,
        }
        self._feature_names: list[str] = []
        self._model = None

    def _lazy_import(self):
        from lightgbm import LGBMClassifier

        return LGBMClassifier(**self.params)

    def fit(
        self, X: npt.NDArray[np.float64] | np.ndarray, y: npt.NDArray[np.int64] | np.ndarray
    ) -> "LightGBMClassifier":
        self._model = self._lazy_import()
        if len(X) > 100:
            split = int(len(X) * 0.9)
            self._model.fit(
                X[:split],
                y[:split],
                eval_set=[(X[split:], y[split:])],
                callbacks=[self._get_early_stopping()],
            )
        else:
            self._model.fit(X, y)
        return self

    @staticmethod
    def _get_early_stopping():
        from lightgbm import early_stopping

        return early_stopping(10, verbose=False)

    def predict(self, X: npt.NDArray[np.float64] | np.ndarray) -> npt.NDArray[np.int64]:
        if self._model is None:
            raise RuntimeError("Model not fitted yet")
        return self._model.predict(X)

    def predict_proba(
        self, X: npt.NDArray[np.float64] | np.ndarray
    ) -> npt.NDArray[np.float64]:
        if self._model is None:
            raise RuntimeError("Model not fitted yet")
        return self._model.predict_proba(X)

    def save(self, path: str | Path) -> None:
        if self._model is None:
            raise RuntimeError("Model not fitted yet")
        joblib.dump({
            "model": self._model,
            "feature_names": self._feature_names,
            "odds_imputer": getattr(self, "_odds_imputer", None),
        }, path)

    @classmethod
    def load(cls, path: str | Path) -> "LightGBMClassifier":
        data = joblib.load(path)
        instance = cls()
        instance._model = data["model"]
        instance._feature_names = data.get("feature_names", [])
        imputer = data.get("odds_imputer")
        if imputer is not None:
            instance._odds_imputer = imputer
        return instance

    @property
    def feature_importance(self) -> dict[str, float]:
        if self._model is None:
            return {}
        importances = self._model.feature_importances_
        if importances is None:
            return {}
        if self._feature_names:
            return dict(zip(self._feature_names, map(float, importances), strict=False))
        return {f"feature_{i}": float(v) for i, v in enumerate(importances)}

    @property
    def model_type(self) -> str:
        return "lightgbm"

    @property
    def model_class(self) -> str:
        return "LGBMClassifier"

    def get_params(self) -> dict:
        return self.params

    def set_params(self, **params) -> None:
        self.params.update(params)

    @property
    def classes_(self) -> list[int]:
        if self._model is None:
            return [0, 1, 2]
        return list(self._model.classes_)
