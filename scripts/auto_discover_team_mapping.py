"""Auto-discover API-Football team name mapping from injury data.

For each league+season, fetches injury data and compares the team names
with DB team names to build a mapping.
"""
import asyncio
import json
import sys
import sqlite3
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sys, io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from betting_bot.services.api_football_client import ApiFootballClient, LEAGUE_IDS

DB_PATH = Path("data/betting_bot.db")

LEAGUE_NAME_TO_AF_ID = {
    "Premier League": 39,
    "La Liga": 140,
    "Serie A": 135,
    "1. Bundesliga": 78,
    "Bundesliga": 78,
    "Ligue 1": 61,
    "Championship": 40,
    "Eredivisie": 88,
    "Primeira Liga": 94,
    "Major League Soccer": 253,
    "FA Women's Super League": 739,
    "Liga F": 712,
    "NWSL": 254,
    "Frauen Bundesliga": 82,
    "Serie A Women": 139,
    "Indian Super league": 323,
}

MATCH_SEASONS = {
    "Ligue 1": [2022, 2023],
    "1. Bundesliga": [2023, 2024],
    "Premier League": [2023, 2024],
    "La Liga": [2023, 2024],
    "Serie A": [2023, 2024],
    "FA Women's Super League": [2023, 2024],
    "Liga F": [2023, 2024],
    "NWSL": [2023, 2024],
    "Frauen Bundesliga": [2023, 2024],
    "Serie A Women": [2023, 2024],
    "Indian Super league": [2022, 2023],
    "Championship": [2023, 2024],
    "Eredivisie": [2023, 2024],
    "Primeira Liga": [2023, 2024],
    "Major League Soccer": [2023, 2024],
}


async def main():
    client = ApiFootballClient()

    conn = sqlite3.connect(str(DB_PATH))
    db_teams_by_league = defaultdict(set)
    for row in conn.execute(
        "SELECT l.name, t.name FROM team t JOIN league l ON t.league_id = l.id"
    ):
        db_teams_by_league[row[0]].add(row[1])
    conn.close()

    mapping = {}

    for league_name, af_id in LEAGUE_NAME_TO_AF_ID.items():
        db_teams = db_teams_by_league.get(league_name, set())
        seasons = MATCH_SEASONS.get(league_name, [2023])

        all_api_teams = set()
        for season in seasons:
            print(f"\n[{league_name}] season {season}...")
            try:
                injuries = await client.get_injuries(league_id=af_id, season=season)
            except Exception as e:
                print(f"  FAILED: {e}")
                continue

            for inj in injuries:
                team = inj.get("team", {}).get("name", "")
                if team:
                    all_api_teams.add(team)

            print(f"  {len(injuries)} injuries, {len(all_api_teams)} unique API team names")

        if all_api_teams:
            print(f"\n  Total unique API team names for {league_name}:")
            league_map = {}

            def normalize(n):
                import unicodedata
                nfkd = unicodedata.normalize("NFKD", n)
                return nfkd.encode("ascii", "ignore").decode("ascii").lower().replace(" ", "")

            for api_name in sorted(all_api_teams):
                api_norm = normalize(api_name)
                matches = []
                for db_name in db_teams:
                    db_norm = normalize(db_name)
                    if api_norm == db_norm:
                        matches.append((db_name, "EXACT"))
                    elif api_norm in db_norm or db_norm in api_norm:
                        matches.append((db_name, "FUZZY"))

                if matches:
                    best = max(matches, key=lambda x: len(x[0]))
                    league_map[api_name] = best[0]
                    print(f"    '{api_name}' -> '{best[0]}' ({best[1]})")
                else:
                    league_map[api_name] = None
                    print(f"    '{api_name}' -> ??? (NO MATCH)")

            mapping[league_name] = league_map
        else:
            print(f"  No data for {league_name}")

    await client.close()

    # Print as JSON for mapping file
    print("\n\n=== MAPPING JSON ===\n")
    print(json.dumps(mapping, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
