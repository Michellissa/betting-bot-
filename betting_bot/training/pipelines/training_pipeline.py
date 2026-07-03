"""Orchestrator for the full model training pipeline."""

from datetime import datetime

import numpy as np
import numpy.typing as npt
import pandas as pd
from loguru import logger
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.core.config import get_settings
from betting_bot.core.constants import DEFAULT_RANDOM_STATE, DEFAULT_TEST_SPLIT
from betting_bot.models.classifiers.base_classifier import BaseClassifier
from betting_bot.models.ensemble.ensemble_manager import EnsembleManager
from betting_bot.models.feature import FeatureStore
from betting_bot.models.match import Match
from betting_bot.training.optimization.optuna_optimizer import OptunaOptimizer
from betting_bot.training.optimization.search_spaces import get_search_space
from betting_bot.training.pipelines.base_trainer import TrainResult
from betting_bot.training.pipelines.classifier_trainer import ClassifierTrainer

ODDS_COLUMNS = [
    "odds_home_prob", "odds_draw_prob", "odds_away_prob",
    "odds_overround", "odds_home_odds_raw", "odds_draw_odds_raw",
    "odds_away_odds_raw",
]

PLAYER_AVAILABILITY_COLUMNS = [
    "home_missing_players_count", "away_missing_players_count",
]


class TrainingPipeline:
    """Orchestrates data loading, training, and model registration."""

    def __init__(
        self,
        db: AsyncSession,
        model_name: str | None = None,
        feature_version: str | None = None,
        model_version: str | None = None,
        optimize: bool = False,
        n_trials: int = 50,
        cv_folds: int = 5,
        test_size: float = DEFAULT_TEST_SPLIT,
        random_state: int = DEFAULT_RANDOM_STATE,
    ) -> None:
        self.db = db
        settings = get_settings()
        self.feature_version = feature_version or settings.TRAINING_FEATURE_VERSION
        self.model_version = model_version or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        self.model_name = model_name
        self.optimize = optimize
        self.n_trials = n_trials
        self.cv_folds = cv_folds
        self.test_size = test_size
        self.random_state = random_state

    async def load_training_data(
        self,
        target: str = "result",
        league_ids: list[int] | None = None,
    ) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.int64], list[str]]:
        """Load features and target from FeatureStore + Match tables."""
        stmt = (
            select(FeatureStore, Match)
            .join(Match, FeatureStore.match_id == Match.id)
            .where(
                and_(
                    FeatureStore.feature_version == self.feature_version,
                    Match.is_finished,
                    Match.result.isnot(None),
                )
            )
            .order_by(Match.match_date)
        )
        if league_ids:
            stmt = stmt.where(Match.league_id.in_(league_ids))

        result = await self.db.execute(stmt)
        rows = result.all()

        if not rows:
            logger.warning("No training data found")
            return np.array([]), np.array([]), []

        # Define feature columns from FeatureStore
        feature_store_columns = [
            col.name for col in FeatureStore.__table__.columns
            if col.name not in (
                "id", "match_id", "feature_version",
                "created_at", "updated_at",
                "temperature", "humidity", "wind_speed", "weather_condition",
                "referee_id", "referee_home_win_rate",
                "odds_source", "player_data_available",
            )
        ]

        data = []
        targets = []
        for fs, match in rows:
            row_data = {}
            for col in feature_store_columns:
                val = getattr(fs, col, None)
                if col in ODDS_COLUMNS or col in PLAYER_AVAILABILITY_COLUMNS:
                    row_data[col] = val  # preserve None (NaN) for later imputation
                else:
                    row_data[col] = val if val is not None else 0.0
            # Add odds_missing indicator
            odds_none = any(
                getattr(fs, c, None) is None for c in ODDS_COLUMNS
                if c in feature_store_columns
            )
            row_data["odds_missing"] = 1.0 if odds_none else 0.0
            # Add player_data_missing indicator
            player_none = any(
                getattr(fs, c, None) is None for c in PLAYER_AVAILABILITY_COLUMNS
                if c in feature_store_columns
            )
            row_data["player_data_missing"] = 1.0 if player_none else 0.0
            data.append(row_data)

            if target == "result":
                result_map = {"H": 0, "D": 1, "A": 2}
                targets.append(result_map.get(match.result, 1))
            elif target == "over_2_5":
                goals = (match.home_goals or 0) + (match.away_goals or 0)
                targets.append(1 if goals > 2.5 else 0)
            elif target == "btts":
                hg = match.home_goals or 0
                ag = match.away_goals or 0
                targets.append(1 if hg > 0 and ag > 0 else 0)

        df = pd.DataFrame(data)
        df = df.dropna(axis=1, how="all")

        X = df.values.astype(np.float64)
        y = np.array(targets, dtype=np.int64)
        feature_names = list(df.columns)

        logger.info(
            f"Loaded {len(X)} samples with {len(feature_names)} features"
        )
        return X, y, feature_names

    def train_test_split(
        self,
        X: npt.NDArray[np.float64],
        y: npt.NDArray[np.int64],
    ) -> tuple[
        npt.NDArray[np.float64], npt.NDArray[np.float64],
        npt.NDArray[np.int64], npt.NDArray[np.int64],
    ]:
        """Split data chronologically (last test_size fraction as test)."""
        n = len(X)
        split_idx = int(n * (1 - self.test_size))
        return (
            X[:split_idx], X[split_idx:],
            y[:split_idx], y[split_idx:],
        )

    @staticmethod
    def impute_sparse_columns(
        X_train: npt.NDArray[np.float64],
        X_test: npt.NDArray[np.float64],
        feature_names: list[str],
    ) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.float64], list[str], list[float]]:
        """Impute NaN sparse columns (odds, player availability) with training median.

        Applies to both odds_* and player availability columns.
        Returns imputed X_train, imputed X_test, updated feature_names, and the
        median values used for imputation (needed at prediction time).
        """
        sparse_col_idxs = [
            i for i, name in enumerate(feature_names)
            if (name.startswith("odds_") and name != "odds_missing")
            or name in PLAYER_AVAILABILITY_COLUMNS
        ]
        if not sparse_col_idxs:
            return X_train, X_test, feature_names, []

        sparse_train = X_train[:, sparse_col_idxs]
        medians = np.nanmedian(sparse_train, axis=0)

        for col_idx, median in zip(sparse_col_idxs, medians):
            if np.isnan(median):
                median = 0.0
            train_nan = np.isnan(X_train[:, col_idx])
            X_train[train_nan, col_idx] = median
            test_nan = np.isnan(X_test[:, col_idx])
            X_test[test_nan, col_idx] = median

        return X_train, X_test, feature_names, medians.tolist()

    async def run(
        self,
        target: str = "result",
        league_ids: list[int] | None = None,
    ) -> list[TrainResult]:
        """Run the full training pipeline.

        Splits data chronologically: the last ``test_size`` fraction
        is held out as a genuine out-of-time test set, never touched
        during CV or training.
        """
        X, y, feature_names = await self.load_training_data(target, league_ids)
        if len(X) == 0:
            logger.error("No training data available")
            return []

        X_train, X_test, y_train, y_test = self.train_test_split(X, y)
        logger.info(
            f"Train: {len(X_train)} samples, Test: {len(X_test)} samples (time-ordered)"
        )

        # Impute sparse columns (odds + player availability): fit on training data only
        X_train, X_test, feature_names, sparse_medians = self.impute_sparse_columns(
            X_train, X_test, feature_names,
        )
        logger.info(
            f"Sparse column imputation: {len(sparse_medians)} columns, "
            f"medians={[f'{m:.3f}' for m in sparse_medians]}"
        )

        if self.model_name:
            model_names = [self.model_name]
        else:
            from betting_bot.core.constants import ModelName
            model_names = [m.value for m in ModelName]

        # Pass imputer to trainer for saving alongside model
        imputer_data = {
            "odds_medians": sparse_medians,
            "odds_column_indices": [
                i for i, n in enumerate(feature_names)
                if (n.startswith("odds_") and n != "odds_missing")
                or n in PLAYER_AVAILABILITY_COLUMNS
            ],
        }

        results = []
        for name in model_names:
            classifier = EnsembleManager.create_classifier_from_name(name)

            if self.optimize:
                logger.info(f"Optimizing hyperparameters for {name}...")
                optimizer = OptunaOptimizer(
                    classifier.__class__,
                    get_search_space(name),
                    n_trials=self.n_trials,
                    cv_folds=self.cv_folds,
                    random_state=self.random_state,
                )
                best_params = optimizer.optimize(X_train, y_train)
                classifier.set_params(**best_params)
                logger.info(f"Best params for {name}: {best_params}")

            trainer = ClassifierTrainer(
                classifier=classifier,
                db=self.db,
                n_folds=self.cv_folds,
                model_version=self.model_version,
                feature_version=self.feature_version,
            )

            result = await trainer.train_and_register(
                X_train, y_train, feature_names,
                target_variable=target,
                X_test=X_test,
                y_test=y_test,
                imputer_data=imputer_data,
            )
            results.append(result)

        return results

    async def run_single(
        self,
        classifier: BaseClassifier,
        X: npt.NDArray[np.float64],
        y: npt.NDArray[np.int64],
        feature_names: list[str],
    ) -> TrainResult:
        """Train and register a single classifier."""
        trainer = ClassifierTrainer(
            classifier=classifier,
            db=self.db,
            n_folds=self.cv_folds,
            model_version=self.model_version,
            feature_version=self.feature_version,
        )
        return await trainer.train_and_register(X, y, feature_names, imputer_data={
            "odds_medians": [],
            "odds_column_indices": [],
        })
