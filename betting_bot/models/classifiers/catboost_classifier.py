"""CatBoost classifier wrapper."""

from pathlib import Path

import numpy as np
import numpy.typing as npt

from betting_bot.models.classifiers.base_classifier import BaseClassifier


class CatBoostClassifier(BaseClassifier):
    """Wrapper around CatBoostClassifier."""

    def __init__(
        self,
        iterations: int = 500,
        depth: int = 8,
        learning_rate: float = 0.05,
        l2_leaf_reg: float = 3.0,
        border_count: int = 128,
        random_state: int = 42,
        thread_count: int = -1,
        **kwargs,
    ) -> None:
        self.params = {
            "iterations": iterations,
            "depth": depth,
            "learning_rate": learning_rate,
            "l2_leaf_reg": l2_leaf_reg,
            "border_count": border_count,
            "random_state": random_state,
            "thread_count": thread_count,
            "verbose": 0,
            **kwargs,
        }
        self._feature_names: list[str] = []
        self._model = None

    def _lazy_import(self):
        from catboost import CatBoostClassifier

        return CatBoostClassifier(**self.params)

    def fit(
        self, X: npt.NDArray[np.float64] | np.ndarray, y: npt.NDArray[np.int64] | np.ndarray
    ) -> "CatBoostClassifier":
        self._model = self._lazy_import()
        if len(X) > 100:
            split = int(len(X) * 0.9)
            self._model.fit(
                X[:split],
                y[:split],
                eval_set=(X[split:], y[split:]),
                verbose=False,
                early_stopping_rounds=10,
            )
        else:
            self._model.fit(X, y, verbose=False)
        return self

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
        self._model.save_model(str(path))
        import json

        meta_path = Path(str(path) + ".meta.json")
        meta_path.write_text(json.dumps({"feature_names": self._feature_names}))

    @classmethod
    def load(cls, path: str | Path) -> "CatBoostClassifier":
        import json

        from catboost import CatBoostClassifier

        instance = cls()
        instance._model = CatBoostClassifier()
        instance._model.load_model(str(path))
        meta_path = Path(str(path) + ".meta.json")
        if meta_path.exists():
            instance._feature_names = json.loads(meta_path.read_text()).get("feature_names", [])
        return instance

    @property
    def feature_importance(self) -> dict[str, float]:
        if self._model is None:
            return {}
        importances = self._model.get_feature_importance()
        if importances is None:
            return {}
        if self._feature_names:
            return dict(zip(self._feature_names, map(float, importances), strict=False))
        return {f"feature_{i}": float(v) for i, v in enumerate(importances)}

    @property
    def model_type(self) -> str:
        return "catboost"

    @property
    def model_class(self) -> str:
        return "CatBoostClassifier"

    def get_params(self) -> dict:
        return self.params

    def set_params(self, **params) -> None:
        self.params.update(params)

    @property
    def classes_(self) -> list[int]:
        if self._model is None:
            return [0, 1, 2]
        return list(self._model.classes_)
