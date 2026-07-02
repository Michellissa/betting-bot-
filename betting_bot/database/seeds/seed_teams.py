"""Seed data for top division teams."""

from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.database.repositories.league_repository import LeagueRepository
from betting_bot.database.repositories.match_repository import TeamRepository

TEAMS_BY_LEAGUE = {
    "PL": [
        "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
        "Chelsea", "Crystal Palace", "Everton", "Fulham", "Ipswich Town",
        "Leicester City", "Liverpool", "Manchester City", "Manchester United",
        "Newcastle United", "Nottingham Forest", "Southampton", "Tottenham",
        "West Ham", "Wolves",
    ],
    "PD": [
        "Athletic Club", "Atlético Madrid", "Barcelona", "Celta Vigo",
        "Espanyol", "Getafe", "Girona", "Las Palmas", "Leganés",
        "Mallorca", "Osasuna", "Rayo Vallecano", "Real Betis",
        "Real Madrid", "Real Sociedad", "Real Valladolid",
        "Sevilla", "Valencia", "Villarreal", "Alavés",
    ],
    "SA": [
        "Atalanta", "Bologna", "Cagliari", "Como", "Empoli",
        "Fiorentina", "Genoa", "Hellas Verona", "Inter", "Juventus",
        "Lazio", "Lecce", "Milan", "Monza", "Napoli",
        "Parma", "Roma", "Torino", "Udinese", "Venezia",
    ],
    "BL1": [
        "Augsburg", "Bayer Leverkusen", "Bayern Munich", "Bochum",
        "Borussia Dortmund", "Borussia Mönchengladbach", "Eintracht Frankfurt",
        "Freiburg", "Heidenheim", "Hoffenheim", "Holstein Kiel",
        "Mainz 05", "RB Leipzig", "SC Freiburg", "St. Pauli",
        "Stuttgart", "Union Berlin", "Werder Bremen", "Wolfsburg",
    ],
    "FL1": [
        "Angers", "Auxerre", "Brest", "Le Havre", "Lens",
        "Lille", "Lyon", "Marseille", "Monaco", "Montpellier",
        "Nantes", "Nice", "Paris Saint-Germain", "Reims", "Rennes",
        "Saint-Étienne", "Strasbourg", "Toulouse",
    ],
}


async def seed_teams(db: AsyncSession) -> None:
    """Seed teams for all configured leagues."""
    league_repo = LeagueRepository(db)
    team_repo = TeamRepository(db)

    for league_code, team_names in TEAMS_BY_LEAGUE.items():
        league = await league_repo.get_by_code(league_code)
        if not league:
            continue

        for team_name in team_names:
            existing = await team_repo.get_by(name=team_name, league_id=league.id)
            if not existing:
                await team_repo.create(
                    name=team_name,
                    league_id=league.id,
                    country=league.country,
                    elo_rating=1500.0,
                )
