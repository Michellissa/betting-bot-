"""Fetch WC 2026 upcoming knockout matches and generate predictions."""

import asyncio
import sys
from pathlib import Path
from datetime import date, datetime

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from betting_bot.core.config import get_settings
from betting_bot.models.match import League, Season, Team, Match
from betting_bot.prediction.predictor import PredictionGenerator
from betting_bot.services.worldcup2026_client import WorldCup2026Client

# Map WC API team names to DB names (where they differ)
TEAM_NAME_MAP = {
    "Cape Verde": "Cape Verde Islands",
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
}


async def main():
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    client = WorldCup2026Client()
    games = await client.get_games()

    upcoming = [
        g for g in games
        if g.get("finished") != "TRUE"
        and str(g.get("home_team_id", "0")) != "0"
        and str(g.get("away_team_id", "0")) != "0"
    ]
    print(f"Upcoming WC 2026 knockout matches: {len(upcoming)}")

    async with session_factory() as db:
        # Find or create WC league
        league = None
        result = await db.execute(select(League).where(League.code == "FIFA WORLD"))
        league = result.scalar_one_or_none()
        if not league:
            league = League(name="FIFA World Cup 2026", code="FIFA WORLD", country="International", is_active=True)
            db.add(league)
            await db.flush()
            print(f"Created league: {league.name} (id={league.id})")

        # Create 2026 season
        result = await db.execute(
            select(Season).where(Season.league_id == league.id, Season.name == "2026")
        )
        season = result.scalar_one_or_none()
        if not season:
            season = Season(
                league_id=league.id,
                name="2026",
                start_date=date(2026, 1, 1),
                end_date=date(2027, 1, 1),
                is_current=True,
            )
            db.add(season)
            await db.flush()
            print(f"Created season: {season.name}")

        total_stored = 0
        for g in upcoming:
            ext_id = f"wc2026_{g['id']}"
            result = await db.execute(select(Match).where(Match.external_id == ext_id))
            if result.scalar_one_or_none():
                continue

            home_name = g.get("home_team_name_en", "").strip()
            away_name = g.get("away_team_name_en", "").strip()

            home_db_name = TEAM_NAME_MAP.get(home_name, home_name)
            away_db_name = TEAM_NAME_MAP.get(away_name, away_name)

            # Find or create home team
            result = await db.execute(
                select(Team).where(Team.name == home_db_name, Team.league_id == league.id)
            )
            home_team = result.scalar_one_or_none()
            if not home_team:
                home_team = Team(name=home_db_name, league_id=league.id, country=g.get("home_team_name_en", ""), elo_rating=1500.0)
                db.add(home_team)
                await db.flush()
                print(f"  Created team: {home_db_name}")

            # Find or create away team
            result = await db.execute(
                select(Team).where(Team.name == away_db_name, Team.league_id == league.id)
            )
            away_team = result.scalar_one_or_none()
            if not away_team:
                away_team = Team(name=away_db_name, league_id=league.id, country=g.get("away_team_name_en", ""), elo_rating=1500.0)
                db.add(away_team)
                await db.flush()
                print(f"  Created team: {away_db_name}")

            # Parse match date
            match_date = None
            date_str = g.get("local_date", "")
            if date_str:
                try:
                    match_date = datetime.strptime(date_str, "%m/%d/%Y %H:%M")
                except ValueError:
                    pass

            match = Match(
                league_id=league.id,
                season_id=season.id,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                match_date=match_date or datetime.now(),
                round=g.get("matchday"),
                venue=None,
                is_finished=False,
                external_id=ext_id,
                source="worldcup2026",
            )
            db.add(match)
            await db.flush()
            total_stored += 1
            print(f"  Stored: {home_db_name} vs {away_db_name} @ {date_str}")

        await db.commit()
        print(f"\nStored {total_stored} WC 2026 matches")

        # Generate predictions
        if total_stored > 0:
            print("\nGenerating predictions...")
            gen = PredictionGenerator(db)
            predictions = await gen.predict_upcoming_matches()
            print(f"Generated {len(predictions)} predictions")

        await db.commit()

    await client.close()
    await engine.dispose()
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
