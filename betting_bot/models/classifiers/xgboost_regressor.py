"""XGBoost regressor wrapper."""

from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from betting_bot.models.classifiers.base_regressor import BaseRegressor


class XGBoostRegressor(BaseRegressor):
    """Wrapper around XGBRegressor."""

    def __init__(
        self,
        n_estimators: int = 500,
        max_depth: int = 6,
        learning_rate: float = 0.05,
        subsample: float = 0.8,
        colsample_bytree: float = 0.8,
        min_child_weight: int = 3,
        gamma: float = 0.1,
        reg_alpha: float = 0.1,
        reg_lambda: float = 1.0,
        random_state: int = 42,
        n_jobs: int = -1,
        **kwargs,
    ) -> None:
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "subsample": subsample,
            "colsample_bytree": colsample_bytree,
            "min_child_weight": min_child_weight,
            "gamma": gamma,
            "reg_alpha": reg_alpha,
            "reg_lambda": reg_lambda,
            "random_state": random_state,
            "n_jobs": n_jobs,
            "verbosity": 0,
            **kwargs,
        }
        self._feature_names: list[str] = []
        self._model: Any | None = None

    def _lazy_import(self):
        import xgboost as xgb
        return xgb.XGBRegressor(**self.params)

    def fit(
        self, X: npt.NDArray[np.float64] | np.ndarray, y: npt.NDArray[np.float64] | np.ndarray
    ) -> "XGBoostRegressor":
        self._model = self._lazy_import()
        if len(X) > 100:
            split = int(len(X) * 0.9)
            eval_set = [(X[split:], y[split:])]
            self._model.fit(
                X[:split],
                y[:split],
                eval_set=eval_set,
                verbose=False,
            )
        else:
            self._model.fit(X, y)
        return self

    def predict(self, X: npt.NDArray[np.float64] | np.ndarray) -> npt.NDArray[np.float64]:
        if self._model is None:
            raise RuntimeError("Model not fitted yet")
        return self._model.predict(X)

    def save(self, path: str | Path) -> None:
        if self._model is None:
            raise RuntimeError("Model not fitted yet")
        self._model.save_model(str(path))
        import json
        meta_path = Path(str(path) + ".meta.json")
        meta_path.write_text(json.dumps({
            "feature_names": self._feature_names,
            "odds_imputer": getattr(self, "_odds_imputer", None),
        }))

    @classmethod
    def load(cls, path: str | Path) -> "XGBoostRegressor":
        import json
        import xgboost as xgb
        instance = cls()
        instance._model = xgb.XGBRegressor()
        instance._model.load_model(str(path))
        meta_path = Path(str(path) + ".meta.json")
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            instance._feature_names = meta.get("feature_names", [])
            imputer = meta.get("odds_imputer")
            if imputer is not None:
                instance._odds_imputer = imputer
        return instance

    @property
    def feature_importance(self) -> dict[str, float]:
        if self._model is None or not hasattr(self._model, "feature_importances_"):
            return {}
        importances = self._model.feature_importances_
        if importances is None:
            return {}
        if self._feature_names:
            return dict(zip(self._feature_names, map(float, importances), strict=False))
        return {f"feature_{i}": float(v) for i, v in enumerate(importances)}

    @property
    def model_type(self) -> str:
        return "xgboost"

    @property
    def model_class(self) -> str:
        return "XGBRegressor"

    def get_params(self) -> dict:
        return self.params

    def set_params(self, **params) -> None:
        self.params.update(params)
