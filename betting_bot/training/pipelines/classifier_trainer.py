"""Classifier trainer with cross-validation and model registry integration."""

import time

import numpy as np
import numpy.typing as npt
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.core.config import get_settings
from betting_bot.database.repositories.base import BaseRepository
from betting_bot.models.classifiers.base_classifier import BaseClassifier
from betting_bot.models.model_registry import ModelMetric, ModelRegistry
from betting_bot.training.pipelines.base_trainer import BaseTrainer, TrainResult


class ClassifierTrainer(BaseTrainer):
    """Trains, evaluates, and registers classifier models."""

    def __init__(
        self,
        classifier: BaseClassifier,
        db: AsyncSession,
        random_state: int = 42,
        n_folds: int = 5,
        model_version: str = "v1.0.0",
        feature_version: str = "v1",
    ) -> None:
        super().__init__(random_state=random_state, n_folds=n_folds)
        self.classifier = classifier
        self.db = db
        self.model_version = model_version
        self.feature_version = feature_version

    async def train(
        self,
        X: npt.NDArray[np.float64],
        y: npt.NDArray[np.int64],
        feature_names: list[str],
        model_config: dict | None = None,
    ) -> TrainResult:
        """Train the classifier with time-respecting CV."""
        start_time = time.time()
        result = TrainResult(
            model_name=self.classifier.model_class,
            model_version=self.model_version,
            feature_version=self.feature_version,
            n_train_samples=len(X),
            n_features=X.shape[1],
            hyperparameters=self.classifier.get_params(),
        )

        # Time-respecting cross-validation
        if self.n_folds > 1 and len(X) >= self.n_folds * 2:
            cv_metrics = self.cross_validate(self.classifier, X, y)
            for metrics in cv_metrics:
                result.cv_accuracy.append(metrics["accuracy"])
                result.cv_f1.append(metrics["f1"])
                result.cv_log_loss.append(metrics["log_loss"])
                result.cv_brier.append(metrics.get("brier", 1.0))
                result.cv_precision.append(metrics["precision"])
                result.cv_recall.append(metrics["recall"])
                result.cv_auc.append(metrics.get("auc", 0.0))
            logger.info(
                f"CV results - Accuracy: {result.avg_cv_accuracy:.4f}, "
                f"F1: {result.avg_cv_f1:.4f}, Log Loss: {result.avg_cv_log_loss:.4f}, "
                f"Brier: {result.avg_cv_brier:.4f}"
            )

        # Train on full training set
        logger.info(f"Training {self.classifier.model_class} on {len(X)} samples...")
        self.classifier.fit(X, y)

        result.training_duration_seconds = time.time() - start_time
        logger.info(
            f"Training completed in {result.training_duration_seconds:.2f}s"
        )
        return result

    async def evaluate(
        self,
        result: TrainResult,
        X_test: npt.NDArray[np.float64],
        y_test: npt.NDArray[np.int64],
    ) -> TrainResult:
        """Evaluate on a genuine held-out test set."""
        y_pred = self.classifier.predict(X_test)
        y_proba = self.classifier.predict_proba(X_test)
        metrics = self.compute_metrics(y_test, y_pred, y_proba)
        result.test_accuracy = metrics["accuracy"]
        result.test_f1 = metrics["f1"]
        result.test_log_loss = metrics["log_loss"]
        result.test_brier = metrics.get("brier", 1.0)
        result.test_precision = metrics["precision"]
        result.test_recall = metrics["recall"]
        result.test_auc = metrics.get("auc", 0.0)

        from sklearn.metrics import confusion_matrix as cm
        cm_matrix = cm(y_test, y_pred)
        result.confusion_matrix = cm_matrix.tolist()

        # Feature importance
        result.feature_importance = self.classifier.feature_importance
        if feature_names_cache := getattr(self, "_feature_names", None):
            importances = self.classifier.feature_importance
            for name in feature_names_cache:
                if name in importances:
                    continue
                result.feature_importance[name] = 1.0
            sorted_imp = sorted(
                result.feature_importance.items(), key=lambda x: x[1], reverse=True
            )
            result.top_features = sorted_imp[:20]

        logger.info(
            f"Holdout evaluation - Accuracy: {result.test_accuracy:.4f}, "
            f"Log Loss: {result.test_log_loss:.4f}, Brier: {result.test_brier:.4f}"
        )
        return result

    async def train_and_register(
        self,
        X: npt.NDArray[np.float64],
        y: npt.NDArray[np.int64],
        feature_names: list[str],
        model_config: dict | None = None,
        target_variable: str = "result",
        X_test: npt.NDArray[np.float64] | None = None,
        y_test: npt.NDArray[np.int64] | None = None,
        imputer_data: dict | None = None,
    ) -> TrainResult:
        """Train, evaluate on holdout, and register the model."""
        self._feature_names = feature_names
        result = await self.train(X, y, feature_names, model_config)
        result.target_variable = target_variable

        # Evaluate on holdout if provided
        if X_test is not None and y_test is not None:
            result = await self.evaluate(result, X_test, y_test)

        # Save model to disk
        settings = get_settings()
        model_dir = settings.MODEL_STORAGE_PATH / self.classifier.model_type
        model_dir.mkdir(parents=True, exist_ok=True)
        model_filename = f"{self.classifier.model_class}_v{self.model_version}.joblib"
        model_path = model_dir / model_filename
        self.classifier._feature_names = feature_names
        if imputer_data:
            self.classifier._odds_imputer = imputer_data
        self.classifier.save(str(model_path))

        # Register in database
        repo = BaseRepository(ModelRegistry, self.db)
        registry_entry = await repo.create(
            model_name=self.classifier.model_class,
            model_version=self.model_version,
            feature_version=self.feature_version,
            model_path=str(model_path),
            model_type=self.classifier.model_type,
            model_class=self.classifier.model_class,
            training_date=result.training_date,
            training_duration_seconds=result.training_duration_seconds,
            n_train_samples=result.n_train_samples,
            n_features=result.n_features,
            target_variable=result.target_variable,
            is_classifier=True,
            hyperparameters=result.hyperparameters,
            feature_importance=result.feature_importance,
            top_features=[f[0] for f in result.top_features],
        )

        # Store test metrics
        metrics_repo = BaseRepository(ModelMetric, self.db)
        for metric_name, metric_value in [
            ("accuracy", result.test_accuracy),
            ("f1", result.test_f1),
            ("log_loss", result.test_log_loss),
            ("brier", result.test_brier),
            ("precision", result.test_precision),
            ("recall", result.test_recall),
            ("auc", result.test_auc),
        ]:
            if metric_value:
                await metrics_repo.create(
                    model_id=registry_entry.id,
                    metric_name=metric_name,
                    metric_value=metric_value,
                    dataset_type="test",
                )

        # Store CV metrics
        for fold, acc in enumerate(result.cv_accuracy):
            await metrics_repo.create(
                model_id=registry_entry.id,
                metric_name="accuracy",
                metric_value=acc,
                dataset_type="validation",
                fold=fold,
            )
        for fold, f1_val in enumerate(result.cv_f1):
            await metrics_repo.create(
                model_id=registry_entry.id,
                metric_name="f1",
                metric_value=f1_val,
                dataset_type="validation",
                fold=fold,
            )
        for fold, brier_val in enumerate(result.cv_brier):
            if brier_val:
                await metrics_repo.create(
                    model_id=registry_entry.id,
                    metric_name="brier",
                    metric_value=brier_val,
                    dataset_type="validation",
                    fold=fold,
                )

        await self.db.commit()
        logger.info(
            f"Model registered in DB (id={registry_entry.id}), saved to {model_path}"
        )
        return result
