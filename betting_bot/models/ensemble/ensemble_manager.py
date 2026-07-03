"""Ensemble manager - orchestrates training and prediction across models."""

from betting_bot.core.constants import ModelName
from betting_bot.models.classifiers.base_classifier import BaseClassifier
from betting_bot.models.classifiers.catboost_classifier import CatBoostClassifier
from betting_bot.models.classifiers.lightgbm_classifier import LightGBMClassifier
from betting_bot.models.classifiers.logistic_regression import LogisticRegressionClassifier
from betting_bot.models.classifiers.random_forest import RandomForestClassifier
from betting_bot.models.classifiers.xgboost_classifier import XGBoostClassifier
from betting_bot.models.ensemble.voting_ensemble import VotingEnsemble


class EnsembleManager:
    """Creates and manages model ensembles."""

    CLASSIFIER_MAP: dict[ModelName, type[BaseClassifier]] = {
        ModelName.LOGISTIC_REGRESSION: LogisticRegressionClassifier,
        ModelName.RANDOM_FOREST: RandomForestClassifier,
        ModelName.XGBOOST: XGBoostClassifier,
        ModelName.LIGHTGBM: LightGBMClassifier,
        ModelName.CATBOOST: CatBoostClassifier,
    }

    @classmethod
    def create_classifier(cls, model_name: ModelName, **params) -> BaseClassifier:
        """Create a single classifier by name."""
        clf_cls = cls.CLASSIFIER_MAP.get(model_name)
        if clf_cls is None:
            raise ValueError(f"Unknown model: {model_name}")
        return clf_cls(**params) if params else clf_cls()

    @classmethod
    def create_voting_ensemble(
        cls,
        model_names: list[ModelName] | None = None,
        weights: list[float] | None = None,
    ) -> VotingEnsemble:
        """Create a voting ensemble from specified model types."""
        if model_names is None:
            model_names = list(ModelName)

        classifiers = []
        for name in model_names:
            clf = cls.create_classifier(name)
            classifiers.append((name.value, clf))

        return VotingEnsemble(classifiers=classifiers, weights=weights)

    @classmethod
    def get_default_ensemble(cls) -> VotingEnsemble:
        """Get the default ensemble (all models, equal weights)."""
        return cls.create_voting_ensemble()

    @classmethod
    def create_classifier_from_name(cls, model_name: str, **params) -> BaseClassifier:
        """Create a classifier from a string model name.

        Accepts both enum values (e.g. 'random_forest') and sklearn
        class names (e.g. 'RandomForestClassifier').
        """
        name_map = {m.value: m for m in ModelName}
        enum_val = name_map.get(model_name)
        if enum_val is None:
            # Fallback: map sklearn class names to enum values
            class_to_enum = {
                "RandomForestClassifier": ModelName.RANDOM_FOREST,
                "XGBClassifier": ModelName.XGBOOST,
                "LGBMClassifier": ModelName.LIGHTGBM,
                "CatBoostClassifier": ModelName.CATBOOST,
                "LogisticRegression": ModelName.LOGISTIC_REGRESSION,
            }
            enum_val = class_to_enum.get(model_name)
        if enum_val is None:
            available = list(name_map.keys())
            raise ValueError(f"Unknown model name: {model_name}. Available: {available}")
        return cls.create_classifier(enum_val, **params)

    @classmethod
    def get_available_models(cls) -> list[ModelName]:
        """Return list of available model names."""
        return list(ModelName)
