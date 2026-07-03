"""Check what team names API-Football uses in injury data for specific leagues."""
import asyncio
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sys, io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from betting_bot.services.api_football_client import ApiFootballClient


async def check_league(lname, af_id, season):
    client = ApiFootballClient()
    print(f"\n=== {lname} (AF ID {af_id}) season {season} ===")
    try:
        injuries = await client.get_injuries(league_id=af_id, season=season)
    except Exception as e:
        print(f"  Error: {e}")
        await client.close()
        return

    teams = Counter()
    for inj in injuries:
        t = inj.get("team", {}).get("name", "?")
        teams[t] += 1

    # Also check fixture dates to see the date range
    dates = set()
    for inj in injuries:
        d = inj.get("fixture", {}).get("date", "")[:10]
        if d:
            dates.add(d)

    print(f"  {len(injuries)} records, {len(teams)} teams, {len(dates)} match dates")
    for t, c in teams.most_common():
        print(f"    {t:35s} ({c} records)")
    await client.close()


async def main():
    # Check all leagues with 2021+ data
    leagues = [
        ("Ligue 1", 61, 2022),
        ("Ligue 1", 61, 2021),
        ("Premier League", 39, 2023),
        ("Serie A", 135, 2023),
        ("La Liga", 140, 2023),
        ("1. Bundesliga", 78, 2024),
        ("FA Women's Super League", 739, 2023),
        ("NWSL", 254, 2023),
        ("Frauen Bundesliga", 82, 2023),
        ("Serie A Women", 139, 2023),
        ("Liga F", 712, 2023),
        ("Indian Super league", 323, 2022),
        ("Championship", 40, 2023),
    ]
    # Only check a few to save API budget
    for lname, af_id, season in leagues[:5]:
        await check_league(lname, af_id, season)


if __name__ == "__main__":
    asyncio.run(main())
