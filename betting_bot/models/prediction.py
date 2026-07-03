"""Database models for predictions and prediction results."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from betting_bot.database.base import Base, IntegerIDMixin, TimestampMixin


class Prediction(IntegerIDMixin, TimestampMixin, Base):
    """A single prediction for a match outcome."""

    match_id: Mapped[int] = MappedColumn(Integer, ForeignKey("match.id"), nullable=False, index=True)
    model_name: Mapped[str] = MappedColumn(String(100), nullable=False, index=True)
    feature_version: Mapped[str] = MappedColumn(String(20), nullable=False)

    # Probabilities
    home_win_probability: Mapped[float | None] = MappedColumn(Float)
    draw_probability: Mapped[float | None] = MappedColumn(Float)
    away_win_probability: Mapped[float | None] = MappedColumn(Float)
    over_2_5_probability: Mapped[float | None] = MappedColumn(Float)
    under_2_5_probability: Mapped[float | None] = MappedColumn(Float)
    btts_yes_probability: Mapped[float | None] = MappedColumn(Float)
    btts_no_probability: Mapped[float | None] = MappedColumn(Float)

    # Expected goals
    home_expected_goals: Mapped[float | None] = MappedColumn(Float)
    away_expected_goals: Mapped[float | None] = MappedColumn(Float)

    # Confidence
    confidence_score: Mapped[float | None] = MappedColumn(Float)
    confidence_level: Mapped[str | None] = MappedColumn(String(20))
    model_confidence: Mapped[float | None] = MappedColumn(Float)
    data_confidence_score: Mapped[float | None] = MappedColumn(Float, nullable=True)

    # Risk
    risk_score: Mapped[float | None] = MappedColumn(Float)
    risk_level: Mapped[str | None] = MappedColumn(String(20))

    # Metadata
    prediction_date: Mapped[datetime] = MappedColumn(DateTime, nullable=False, default=datetime.utcnow)
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)
    model_version: Mapped[str | None] = MappedColumn(String(20))
    explanation: Mapped[str | None] = MappedColumn(Text, nullable=True)

    # Relationships
    match: Mapped["Match"] = relationship("Match")
    results: Mapped[list["PredictionResult"]] = relationship(
        "PredictionResult", back_populates="prediction", cascade="all, delete-orphan"
    )


class ModelPrediction(IntegerIDMixin, TimestampMixin, Base):
    """Intermediate predictions from each model before ensemble."""

    match_id: Mapped[int] = MappedColumn(Integer, ForeignKey("match.id"), nullable=False, index=True)
    prediction_id: Mapped[int] = MappedColumn(Integer, ForeignKey("prediction.id"), nullable=False, index=True)
    model_name: Mapped[str] = MappedColumn(String(100), nullable=False)

    home_win_probability: Mapped[float | None] = MappedColumn(Float)
    draw_probability: Mapped[float | None] = MappedColumn(Float)
    away_win_probability: Mapped[float | None] = MappedColumn(Float)

    match: Mapped["Match"] = relationship("Match")
    prediction: Mapped["Prediction"] = relationship("Prediction")


class PredictionResult(IntegerIDMixin, TimestampMixin, Base):
    """Actual outcome after a match is played - for evaluation."""

    prediction_id: Mapped[int] = MappedColumn(Integer, ForeignKey("prediction.id"), nullable=False, index=True)
    match_id: Mapped[int] = MappedColumn(Integer, ForeignKey("match.id"), nullable=False)

    actual_home_goals: Mapped[int | None] = MappedColumn(Integer)
    actual_away_goals: Mapped[int | None] = MappedColumn(Integer)
    actual_result: Mapped[str | None] = MappedColumn(String(1))
    was_correct: Mapped[bool | None] = MappedColumn(Boolean)
    was_profitable: Mapped[bool | None] = MappedColumn(Boolean)
    roi: Mapped[float | None] = MappedColumn(Float)
    profit_loss: Mapped[float | None] = MappedColumn(Float)

    prediction: Mapped["Prediction"] = relationship("Prediction", back_populates="results")
    match: Mapped["Match"] = relationship("Match")
