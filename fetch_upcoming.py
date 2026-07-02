"""Fetch upcoming fixtures from API-FOOTBALL and generate predictions."""

import asyncio
import sys
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from betting_bot.core.config import get_settings
from betting_bot.services.api_football_client import ApiFootballClient, LEAGUE_IDS
from betting_bot.database.repositories.league_repository import LeagueRepository
from betting_bot.database.repositories.match_repository import MatchRepository, TeamRepository
from betting_bot.models.match import League as LeagueModel
from betting_bot.prediction.predictor import PredictionGenerator


async def main():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    api = ApiFootballClient()

    async with session_factory() as db:
        league_repo = LeagueRepository(db)
        team_repo = TeamRepository(db)
        match_repo = MatchRepository(db)

        today = date.today()
        current_season = today.year
        # If we're past July, next season is current_year+1
        if today.month >= 7:
            season_year = current_season
        else:
            season_year = current_season - 1

        # Reverse map: league code -> API-FOOTBALL league_id
        # Key is DB code (e.g. "PL"), value is API-FOOTBALL id (e.g. 39)
        CODE_TO_API_ID = {
            "PL": 39, "PD": 140, "SA": 135, "BL1": 78, "FL1": 61,
            "ELC": 40, "DED": 88, "PPL": 94, "CL": 2,
        }

        total_stored = 0
        total_errors = 0

        for code, api_league_id in CODE_TO_API_ID.items():
            # Find the league in our DB
            db_league = await league_repo.get_by_code(code)
            if not db_league:
                print(f"League {code} not found in DB, skipping")
                continue

            print(f"\n=== Fetching {code} (API id={api_league_id}, season={season_year}) ===")

            try:
                fixtures = await api.get_fixtures(
                    league_id=api_league_id,
                    season=season_year,
                    status="NS",  # Not Started
                    limit=50,
                )
            except Exception as e:
                print(f"  API error for {code}: {e}")
                total_errors += 1
                continue

            if not fixtures:
                print(f"  No upcoming fixtures for {code}")
                continue

            print(f"  Got {len(fixtures)} upcoming fixtures")

            for raw in fixtures:
                parsed = api.parse_fixture(raw)
                match_date = parsed.get("match_date")
                if not match_date:
                    continue

                # Check if match already exists
                existing = await match_repo.get_by(external_id=parsed["external_id"])
                if existing:
                    continue

                # Find or create home team
                home_name = parsed["home_team_name"]
                home_team = await team_repo.get_by(name=home_name, league_id=db_league.id)
                if not home_team:
                    home_team = await team_repo.create(
                        name=home_name,
                        league_id=db_league.id,
                        country=parsed.get("league_country", ""),
                        elo_rating=1500.0,
                    )

                # Find or create away team
                away_name = parsed["away_team_name"]
                away_team = await team_repo.get_by(name=away_name, league_id=db_league.id)
                if not away_team:
                    away_team = await team_repo.create(
                        name=away_name,
                        league_id=db_league.id,
                        country=parsed.get("league_country", ""),
                        elo_rating=1500.0,
                    )

                # Find or create season
                from sqlalchemy import select
                from betting_bot.models.match import Season

                season_name = str(season_year)
                stmt = select(Season).where(
                    Season.league_id == db_league.id,
                    Season.name == season_name,
                )
                result = await db.execute(stmt)
                season = result.scalar_one_or_none()

                if not season:
                    from datetime import date as dt_date
                    season = Season(
                        league_id=db_league.id,
                        name=season_name,
                        start_date=dt_date(season_year, 1, 1),
                        end_date=dt_date(season_year + 1, 1, 1),
                        is_current=True,
                    )
                    db.add(season)
                    await db.flush()

                # Store match
                await match_repo.create(
                    league_id=db_league.id,
                    season_id=season.id,
                    home_team_id=home_team.id,
                    away_team_id=away_team.id,
                    match_date=match_date,
                    round=parsed.get("round"),
                    venue=parsed.get("venue"),
                    home_goals=None,
                    away_goals=None,
                    is_finished=False,
                    external_id=parsed["external_id"],
                    source="api_football",
                )
                total_stored += 1
                match_day = match_date.strftime("%Y-%m-%d %H:%M") if match_date else "?"
                print(f"  Stored: {home_name} vs {away_name} ({match_day})")

        await db.commit()
        print(f"\n=== Stored {total_stored} upcoming matches, {total_errors} errors ===")

        # Now generate predictions for all upcoming matches
        if total_stored > 0:
            print(f"\n=== Generating predictions for upcoming matches ===")
            gen = PredictionGenerator(db)
            predictions = await gen.predict_upcoming_matches()
            print(f"Generated {len(predictions)} predictions")

        await db.commit()

    await api.close()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
