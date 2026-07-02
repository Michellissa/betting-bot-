"""Run all seed scripts."""

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.database.seeds.seed_leagues import seed_leagues
from betting_bot.database.seeds.seed_teams import seed_teams


async def seed_database(db: AsyncSession) -> None:
    """Seed the database with initial data."""
    logger.info("Starting database seeding...")

    league_ids = await seed_leagues(db)
    logger.info(f"Seeded {len(league_ids)} leagues")

    await seed_teams(db)
    logger.info("Seeded teams")

    await db.commit()
    logger.info("Database seeding completed")
