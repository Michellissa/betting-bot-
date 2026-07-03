"""Voting and stacking ensemble classifiers."""

from pathlib import Path

import joblib
import numpy as np
import numpy.typing as npt

from betting_bot.models.classifiers.base_classifier import BaseClassifier
from betting_bot.models.classifiers.logistic_regression import LogisticRegressionClassifier


class VotingEnsemble(BaseClassifier):
    """Soft voting ensemble of multiple classifiers."""

    def __init__(
        self,
        classifiers: list[tuple[str, BaseClassifier]] | None = None,
        weights: list[float] | None = None,
    ) -> None:
        self.classifiers = classifiers or []
        self.weights = weights
        self._feature_names: list[str] = []
        self._is_fitted = False

    def add_classifier(self, name: str, classifier: BaseClassifier, weight: float = 1.0) -> None:
        self.classifiers.append((name, classifier))
        if self.weights is not None:
            self.weights.append(weight)

    def fit(
        self, X: npt.NDArray[np.float64] | np.ndarray, y: npt.NDArray[np.int64] | np.ndarray
    ) -> "VotingEnsemble":
        if not self.classifiers:
            raise ValueError("No classifiers in ensemble")
        for _, clf in self.classifiers:
            clf.fit(X, y)
        self._is_fitted = True
        return self

    def predict(self, X: npt.NDArray[np.float64] | np.ndarray) -> npt.NDArray[np.int64]:
        proba = self.predict_proba(X)
        return np.argmax(proba, axis=1)

    def predict_proba(
        self, X: npt.NDArray[np.float64] | np.ndarray
    ) -> npt.NDArray[np.float64]:
        if not self._is_fitted:
            raise RuntimeError("Ensemble not fitted yet")

        all_probas = []
        weight_sum = 0.0

        for i, (_, clf) in enumerate(self.classifiers):
            proba = clf.predict_proba(X)
            w = self.weights[i] if self.weights else 1.0
            all_probas.append(proba * w)
            weight_sum += w

        if weight_sum == 0:
            return np.mean(all_probas, axis=0)

        return np.sum(all_probas, axis=0) / weight_sum

    def save(self, path: str | Path) -> None:
        data = {
            "classifiers": [
                (name, clf.model_type, clf.model_class) for name, clf in self.classifiers
            ],
            "weights": self.weights,
            "feature_names": self._feature_names,
            "odds_imputer": getattr(self, "_odds_imputer", None),
        }
        joblib.dump(data, path)
        base = Path(path)
        clf_dir = base.parent / f"{base.stem}_classifiers"
        clf_dir.mkdir(exist_ok=True)
        for i, (name, clf) in enumerate(self.classifiers):
            clf_path = clf_dir / f"{i}_{name}.joblib"
            clf.save(str(clf_path))

    @classmethod
    def load(cls, path: str | Path) -> "VotingEnsemble":
        data = joblib.load(path)
        instance = cls()
        base = Path(path)
        clf_dir = base.parent / f"{base.stem}_classifiers"
        classifiers = []
        for i, (name, _, _) in enumerate(data["classifiers"]):
            clf_path = clf_dir / f"{i}_{name}.joblib"
            clf = cls._load_single(clf_path)
            classifiers.append((name, clf))
        instance.classifiers = classifiers
        instance.weights = data.get("weights")
        instance._feature_names = data.get("feature_names", [])
        imputer = data.get("odds_imputer")
        if imputer is not None:
            instance._odds_imputer = imputer
        instance._is_fitted = True
        return instance

    @staticmethod
    def _load_single(path: Path) -> BaseClassifier:
        data = joblib.load(path)
        if isinstance(data, dict) and "model" in data:
            model_type = data["model"].__class__.__name__
        else:
            model_type = "unknown"

        from betting_bot.models.classifiers.catboost_classifier import CatBoostClassifier
        from betting_bot.models.classifiers.lightgbm_classifier import LightGBMClassifier
        from betting_bot.models.classifiers.random_forest import RandomForestClassifier
        from betting_bot.models.classifiers.xgboost_classifier import XGBoostClassifier

        registry = {
            "LogisticRegression": LogisticRegressionClassifier,
            "RandomForestClassifier": RandomForestClassifier,
            "XGBClassifier": XGBoostClassifier,
            "LGBMClassifier": LightGBMClassifier,
            "CatBoostClassifier": CatBoostClassifier,
        }
        cls_type = registry.get(model_type)
        if cls_type:
            return cls_type.load(str(path))
        return LogisticRegressionClassifier.load(str(path))

    @property
    def feature_importance(self) -> dict[str, float]:
        combined: dict[str, float] = {}
        for _, clf in self.classifiers:
            for name, imp in clf.feature_importance.items():
                combined[name] = combined.get(name, 0.0) + imp
        n = len(self.classifiers)
        return {k: v / n for k, v in combined.items()}

    @property
    def model_type(self) -> str:
        return "ensemble"

    @property
    def model_class(self) -> str:
        return "VotingEnsemble"

    def get_params(self) -> dict:
        return {
            "n_classifiers": len(self.classifiers),
            "weights": self.weights,
            "classifiers": [clf.get_params() for _, clf in self.classifiers],
        }

    def set_params(self, **params) -> None:
        pass
