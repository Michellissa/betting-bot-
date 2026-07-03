"""Discover API-Football team names for team mapping.

Queries API-Football teams endpoint for each league, prints API team names
alongside current DB team names for manual mapping verification.

Usage:
    py -3 scripts/discover_api_football_teams.py
"""
import asyncio
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sys; import io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from loguru import logger

from betting_bot.services.api_football_client import ApiFootballClient, LEAGUE_IDS

DB_PATH = Path("data/betting_bot.db")


def get_db_teams_by_league() -> dict[str, list[str]]:
    """Get team names from DB grouped by league code."""
    conn = sqlite3.connect(str(DB_PATH))
    teams_by_league: dict[str, list[str]] = {}
    for row in conn.execute(
        "SELECT l.code, t.name FROM team t JOIN league l ON t.league_id = l.id ORDER BY l.code, t.name"
    ):
        code = row[0]
        name = row[1]
        if code not in teams_by_league:
            teams_by_league[code] = []
        teams_by_league[code].append(name)
    conn.close()
    return teams_by_league


AF_LEAGUE_TO_DB_CODE = {
    39: "PL",
    140: "PD",
    135: "SA",
    78: "BL1",
    61: "FL1",
    40: "ELC",
    88: "DED",
    94: "PPL",
    2: "CL",
}


async def main():
    client = ApiFootballClient()
    db_teams = get_db_teams_by_league()

    for af_league_id, db_code in sorted(AF_LEAGUE_TO_DB_CODE.items()):
        logger.info(f"Fetching teams for API-Football league {af_league_id} (DB code: {db_code})")
        try:
            teams = await client.get_teams(af_league_id, 2024)
        except Exception as e:
            logger.warning(f"Failed for league {af_league_id}: {e}")
            continue

        api_team_names = []
        for t in teams:
            team_data = t.get("team", {})
            name = team_data.get("name", "?")
            api_team_names.append(name)

        api_team_names.sort()
        print(f"\n{'='*60}")
        print(f"API-Football League {af_league_id} (DB: {db_code})")
        print(f"{'='*60}")
        print(f"API team names ({len(api_team_names)}):")
        for name in api_team_names:
            print(f"  - {name}")

        db_names = db_teams.get(db_code, [])
        if db_names:
            print(f"\nDB team names ({len(db_names)}):")
            for name in db_names:
                print(f"  - {name}")

            print(f"\n{' UNMAPPED API TEAMS ':-^60}")
            for api_name in api_team_names:
                found = False
                for db_name in db_names:
                    key = api_name.lower().replace(" ", "")
                    db_key = db_name.lower().replace(" ", "")
                    if key == db_key or key in db_key or db_key in key:
                        found = True
                        break
                if not found:
                    print(f"  API: '{api_name}' <-> DB: ???")

        if len(api_team_names) < 5:
            # Print full response for small leagues
            for t in teams:
                team_data = t.get("team", {})
                print(f"  {json.dumps(team_data, indent=2)}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
