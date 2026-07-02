"""Database models for machine learning model registry."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from betting_bot.database.base import Base, IntegerIDMixin, TimestampMixin


class ModelRegistry(IntegerIDMixin, TimestampMixin, Base):
    """Registry of trained ML models with metadata."""

    model_name: Mapped[str] = MappedColumn(String(100), nullable=False, index=True)
    model_version: Mapped[str] = MappedColumn(String(20), nullable=False)
    feature_version: Mapped[str] = MappedColumn(String(20), nullable=False)

    # File path to serialized model
    model_path: Mapped[str] = MappedColumn(String(500), nullable=False)
    model_type: Mapped[str] = MappedColumn(String(50), nullable=False)  # sklearn, xgboost, lightgbm, catboost
    model_class: Mapped[str] = MappedColumn(String(200), nullable=False)

    # Training metadata
    training_date: Mapped[datetime] = MappedColumn(DateTime, nullable=False)
    training_duration_seconds: Mapped[float | None] = MappedColumn(Float)
    training_data_start: Mapped[datetime | None] = MappedColumn(DateTime)
    training_data_end: Mapped[datetime | None] = MappedColumn(DateTime)
    n_train_samples: Mapped[int | None] = MappedColumn(Integer)
    n_features: Mapped[int | None] = MappedColumn(Integer)

    # Target type
    target_variable: Mapped[str] = MappedColumn(String(50), nullable=False)  # result, over_2_5, btts
    is_classifier: Mapped[bool] = MappedColumn(Boolean, default=True)
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    # Hyperparameters
    hyperparameters: Mapped[dict | None] = MappedColumn(JSON)

    # Feature importance
    feature_importance: Mapped[dict | None] = MappedColumn(JSON)
    top_features: Mapped[list | None] = MappedColumn(JSON)

    # Relationships
    metrics: Mapped[list["ModelMetric"]] = relationship(
        "ModelMetric", back_populates="model", cascade="all, delete-orphan"
    )


class ModelMetric(IntegerIDMixin, TimestampMixin, Base):
    """Evaluation metrics for a trained model."""

    model_id: Mapped[int] = MappedColumn(Integer, ForeignKey("model_registry.id"), nullable=False, index=True)
    metric_name: Mapped[str] = MappedColumn(String(50), nullable=False)
    metric_value: Mapped[float] = MappedColumn(Float, nullable=False)
    dataset_type: Mapped[str] = MappedColumn(String(20), nullable=False)  # train, test, validation
    fold: Mapped[int | None] = MappedColumn(Integer)  # Cross-validation fold number

    model: Mapped["ModelRegistry"] = relationship("ModelRegistry", back_populates="metrics")
