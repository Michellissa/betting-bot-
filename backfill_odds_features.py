"""Backfill pre-match odds features from football-data.co.uk into FeatureStore.

Usage:
    py -3 -m backfill_odds_features

This downloads odds CSVs, maps team names, and stores normalized
implied probabilities for all finished historical matches.
"""
import asyncio

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.database.session import get_async_session
from betting_bot.features.pipelines.odds_features import OddsFeaturesPipeline


async def main():
    async for db in get_async_session():
        pipeline = OddsFeaturesPipeline(db)
        count = await pipeline.backfill_all()
        logger.info(f"Backfill complete: {count} matches with odds features")
        if count == 0:
            logger.warning("No odds features were stored. Check team mappings and CSV availability.")


if __name__ == "__main__":
    asyncio.run(main())
