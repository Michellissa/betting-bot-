"""Backfill player availability features (injuries/suspensions) into FeatureStore.

Uses API-Football injuries endpoint to identify missing players per match.
Stores aggregate counts (not per-player data) as features.

Usage:
    py -3 -m backfill_player_availability_features

This queries API-Football per league+season (max ~24 API calls for 8 leagues × 3 seasons),
maps team names via the manual mapping file, and stores counts in FeatureStore.
"""
import asyncio

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.database.session import get_async_session
from betting_bot.features.pipelines.player_availability_features import PlayerAvailabilityPipeline


async def main():
    async for db in get_async_session():
        pipeline = PlayerAvailabilityPipeline(db)
        count = await pipeline.backfill_all()
        logger.info(f"Backfill complete: {count} matches with player availability features")
        if count == 0:
            logger.warning("No player availability features were stored. Check team mappings and API availability.")


if __name__ == "__main__":
    asyncio.run(main())
