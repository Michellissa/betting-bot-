"""Seed data for leagues and seasons."""

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.database.repositories.league_repository import LeagueRepository, SeasonRepository

LEAGUES = [
    {"name": "Premier League", "code": "PL", "country": "England"},
    {"name": "La Liga", "code": "PD", "country": "Spain"},
    {"name": "Serie A", "code": "SA", "country": "Italy"},
    {"name": "Bundesliga", "code": "BL1", "country": "Germany"},
    {"name": "Ligue 1", "code": "FL1", "country": "France"},
    {"name": "Championship", "code": "ELC", "country": "England"},
    {"name": "Eredivisie", "code": "DED", "country": "Netherlands"},
    {"name": "Primeira Liga", "code": "PPL", "country": "Portugal"},
    {"name": "Allsvenskan", "code": "ALL", "country": "Sweden"},
    {"name": "MLS", "code": "MLS", "country": "USA"},
    {"name": "Brasileirão Série A", "code": "BSA", "country": "Brazil"},
    {"name": "Argentina Primera", "code": "ARP", "country": "Argentina"},
]

SEASONS = [
    {"name": "2023/2024", "start_date": date(2023, 8, 1), "end_date": date(2024, 5, 31), "is_current": False},
    {"name": "2024/2025", "start_date": date(2024, 8, 1), "end_date": date(2025, 5, 31), "is_current": True},
    {"name": "2025/2026", "start_date": date(2025, 8, 1), "end_date": date(2026, 5, 31), "is_current": False},
]


async def seed_leagues(db: AsyncSession) -> list[int]:
    """Seed leagues and return their IDs."""
    league_repo = LeagueRepository(db)
    season_repo = SeasonRepository(db)
    league_ids = []

    for league_data in LEAGUES:
        existing = await league_repo.get_by_code(league_data["code"])
        if existing:
            league_ids.append(existing.id)
            continue

        league = await league_repo.create(**league_data)
        league_ids.append(league.id)

        for season_data in SEASONS:
            existing_season = await season_repo.get_by(
                league_id=league.id, name=season_data["name"]
            )
            if not existing_season:
                await season_repo.create(league_id=league.id, **season_data)

    return league_ids
