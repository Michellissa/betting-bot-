"""Base classes for feature engineering pipelines."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy import select, desc, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.core.constants import FeatureCategory


class BaseFeaturePipeline(ABC):
    """Abstract base class for all feature pipelines.

    Each pipeline computes a specific category of features
    for a given match and returns them as a flat dictionary.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.category: FeatureCategory | None = None

    @abstractmethod
    async def compute(self, match_id: int) -> dict[str, Any]:
        """Compute features for a single match.

        Args:
            match_id: The match to compute features for.

        Returns:
            Dictionary of feature name -> value.
        """
        ...

    @property
    @abstractmethod
    def feature_names(self) -> list[str]:
        """Return list of feature names this pipeline produces."""
        ...

    async def compute_batch(
        self, match_ids: list[int]
    ) -> list[dict[str, Any]]:
        """Compute features for multiple matches."""
        results = []
        for match_id in match_ids:
            try:
                features = await self.compute(match_id)
                results.append(features)
            except Exception as e:
                logger.error(f"Error computing features for match {match_id}: {e}")
                results.append({})
        return results

    def safe_avg(self, values: Sequence[float | None], default: float = 0.0) -> float:
        """Calculate average, ignoring None values."""
        clean = [v for v in values if v is not None]
        if not clean:
            return default
        return float(np.mean(clean))

    def safe_sum(self, values: Sequence[float | None], default: float = 0.0) -> float:
        """Calculate sum, ignoring None values."""
        clean = [v for v in values if v is not None]
        if not clean:
            return default
        return float(np.sum(clean))


class FeatureEngineeringService:
    """Orchestrates multiple feature pipelines and stores results."""

    def __init__(self, db: AsyncSession, feature_version: str = "v1") -> None:
        self.db = db
        self.feature_version = feature_version
        self.pipelines: list[BaseFeaturePipeline] = []

    def add_pipeline(self, pipeline: BaseFeaturePipeline) -> None:
        """Register a feature pipeline."""
        self.pipelines.append(pipeline)

    def add_pipelines(self, pipelines: list[BaseFeaturePipeline]) -> None:
        """Register multiple feature pipelines."""
        self.pipelines.extend(pipelines)

    async def compute_match_features(
        self, match_id: int
    ) -> dict[str, Any]:
        """Compute all features for a single match."""
        all_features: dict[str, Any] = {}

        for pipeline in self.pipelines:
            try:
                features = await pipeline.compute(match_id)
                all_features.update(features)
            except Exception as e:
                logger.error(
                    f"Pipeline {pipeline.__class__.__name__} failed for "
                    f"match {match_id}: {e}"
                )

        return all_features

    async def store_features(
        self, match_id: int, features: dict[str, Any]
    ) -> None:
        """Store computed features in the database."""
        from betting_bot.database.repositories.base import BaseRepository
        from betting_bot.models.feature import FeatureStore

        repo = BaseRepository(FeatureStore, self.db)

        existing = await repo.get_by(
            match_id=match_id,
            feature_version=self.feature_version,
        )

        if existing:
            for key, value in features.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
        else:
            await repo.create(
                match_id=match_id,
                feature_version=self.feature_version,
                **features,
            )

    async def compute_and_store(
        self,
        match_ids: list[int] | None = None,
        league_id: int | None = None,
    ) -> int:
        """Compute and store features for matches.

        If match_ids is None, computes for all unfinished matches
        or matches in a specific league.
        """
        from betting_bot.models.match import Match

        if match_ids is None:
            stmt = select(Match.id)
            if league_id is not None:
                stmt = stmt.where(Match.league_id == league_id)
            result = await self.db.execute(stmt)
            match_ids = [row[0] for row in result.all()]

        count = 0
        for match_id in match_ids:
            features = await self.compute_match_features(match_id)
            if features:
                await self.store_features(match_id, features)
                count += 1

        await self.db.commit()
        return count

    def get_feature_names(self) -> list[str]:
        """Get all feature names from all pipelines."""
        names = []
        for pipeline in self.pipelines:
            names.extend(pipeline.feature_names)
        return names
