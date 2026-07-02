"""Compute features + train all models on StatsBomb data."""
import asyncio
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.database.session import get_async_session
from betting_bot.features.pipelines.advanced_features import AdvancedFeaturesPipeline
from betting_bot.features.pipelines.base_pipeline import FeatureEngineeringService
from betting_bot.features.pipelines.elo_features import EloFeaturesPipeline
from betting_bot.features.pipelines.form_features import FormFeaturesPipeline
from betting_bot.features.pipelines.goal_features import GoalFeaturesPipeline
from betting_bot.features.pipelines.h2h_features import H2HFeaturesPipeline
from betting_bot.features.pipelines.xg_features import XgFeaturesPipeline
from betting_bot.models.match import Match
from betting_bot.training.pipelines.training_pipeline import TrainingPipeline


async def compute_all_features(db: AsyncSession):
    """Compute features for all finished matches."""
    logger.info("Computing features for all finished matches...")
    svc = FeatureEngineeringService(db, "v1")
    svc.add_pipelines([
        FormFeaturesPipeline(db),
        GoalFeaturesPipeline(db),
        XgFeaturesPipeline(db),
        EloFeaturesPipeline(db),
        H2HFeaturesPipeline(db),
        AdvancedFeaturesPipeline(db),
    ])
    stmt = select(Match.id).where(Match.is_finished).where(Match.result.isnot(None))
    result = await db.execute(stmt)
    match_ids = [row[0] for row in result.all()]
    logger.info(f"Computing features for {len(match_ids)} matches...")
    count = 0
    for i, mid in enumerate(match_ids):
        try:
            features = await svc.compute_match_features(mid)
            if features:
                await svc.store_features(mid, features)
                count += 1
        except Exception as e:
            logger.error(f"Failed match {mid}: {e}")
        if (i + 1) % 200 == 0:
            await db.commit()
            logger.info(f"  Progress: {i+1}/{len(match_ids)} features computed")
    await db.commit()
    logger.info(f"Stored features for {count}/{len(match_ids)} matches")
    return count


async def train_models(db: AsyncSession, target: str):
    """Train models for a specific target."""
    logger.info(f"Training models for target='{target}'...")
    pipeline = TrainingPipeline(
        db=db,
        feature_version="v1",
        optimize=False,
        cv_folds=5,
    )
    results = await pipeline.run(target=target)
    for r in results:
        logger.info(
            f"  {r.model_name} ({target}): "
            f"acc={r.test_accuracy:.4f}, f1={r.test_f1:.4f}, "
            f"log_loss={r.test_log_loss:.4f}"
        )
    return results


async def main():
    async for db in get_async_session():
        n = await compute_all_features(db)
        if n == 0:
            logger.error("No features computed. Cannot train.")
            return
        for target in ("result", "over_2_5", "btts"):
            await train_models(db, target)
        logger.info("All training complete!")


if __name__ == "__main__":
    asyncio.run(main())
