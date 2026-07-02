"""Regressor trainer with model registry integration."""

import time

import numpy as np
import numpy.typing as npt
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.core.config import get_settings
from betting_bot.database.repositories.base import BaseRepository
from betting_bot.models.classifiers.base_regressor import BaseRegressor
from betting_bot.models.model_registry import ModelMetric, ModelRegistry


class RegressorTrainer:
    """Trains, evaluates, and registers regression models."""

    def __init__(
        self,
        regressor: BaseRegressor,
        db: AsyncSession,
        model_version: str = "v1.0.0",
        feature_version: str = "v1",
    ) -> None:
        self.regressor = regressor
        self.db = db
        self.model_version = model_version
        self.feature_version = feature_version

    async def train(
        self,
        X: npt.NDArray[np.float64],
        y: npt.NDArray[np.float64],
        feature_names: list[str],
    ) -> dict:
        """Train the regressor and return metrics."""
        start_time = time.time()

        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        from sklearn.model_selection import train_test_split

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        logger.info(f"Training {self.regressor.model_class} on {len(X_train)} samples...")
        self.regressor._feature_names = feature_names
        self.regressor.fit(X_train, y_train)

        y_pred = self.regressor.predict(X_test)
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))

        # Within-1-goal accuracy
        within_1 = float(np.mean(np.abs(y_pred - y_test) < 1.0))
        # Exact match accuracy
        exact_acc = float(np.mean(np.round(y_pred) == y_test))

        duration = time.time() - start_time
        logger.info(
            f"Regression completed in {duration:.2f}s - "
            f"MAE={mae:.4f} RMSE={rmse:.4f} R2={r2:.4f} "
            f"Within1={within_1:.1%} Exact={exact_acc:.1%}"
        )

        return {
            "mae": mae,
            "rmse": rmse,
            "r2": r2,
            "within_1_goal": within_1,
            "exact_accuracy": exact_acc,
            "training_duration_seconds": duration,
            "n_train_samples": len(X_train),
            "n_test_samples": len(X_test),
        }

    async def train_and_register(
        self,
        X: npt.NDArray[np.float64],
        y: npt.NDArray[np.float64],
        feature_names: list[str],
        target_variable: str = "home_goals",
    ) -> dict:
        """Train and register in ModelRegistry."""
        metrics = await self.train(X, y, feature_names)
        metrics["target_variable"] = target_variable

        settings = get_settings()
        model_dir = settings.MODEL_STORAGE_PATH / self.regressor.model_type
        model_dir.mkdir(parents=True, exist_ok=True)
        model_filename = f"{self.regressor.model_class}_v{self.model_version}.joblib"
        model_path = model_dir / model_filename
        self.regressor._feature_names = feature_names
        self.regressor.save(str(model_path))

        repo = BaseRepository(ModelRegistry, self.db)
        registry_entry = await repo.create(
            model_name=self.regressor.model_class,
            model_version=self.model_version,
            feature_version=self.feature_version,
            model_path=str(model_path),
            model_type=self.regressor.model_type,
            model_class=self.regressor.model_class,
            training_date=__import__("datetime").datetime.utcnow(),
            training_duration_seconds=metrics["training_duration_seconds"],
            n_train_samples=metrics["n_train_samples"],
            n_features=len(feature_names),
            target_variable=target_variable,
            is_classifier=False,
            hyperparameters=self.regressor.get_params(),
            feature_importance=self.regressor.feature_importance,
            top_features=[f[0] for f in sorted(
                self.regressor.feature_importance.items(), key=lambda x: x[1], reverse=True
            )[:20]],
        )

        metrics_repo = BaseRepository(ModelMetric, self.db)
        for metric_name, metric_value in [
            ("mae", metrics["mae"]),
            ("rmse", metrics["rmse"]),
            ("r2", metrics["r2"]),
            ("within_1_goal", metrics["within_1_goal"]),
            ("exact_accuracy", metrics["exact_accuracy"]),
        ]:
            await metrics_repo.create(
                model_id=registry_entry.id,
                metric_name=metric_name,
                metric_value=metric_value,
                dataset_type="test",
            )

        await self.db.commit()
        return metrics
