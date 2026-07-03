"""Debug script to verify API-Football injury data matching."""
import asyncio
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from betting_bot.services.api_football_client import ApiFootballClient


async def test():
    client = ApiFootballClient()
    injuries = await client.get_injuries(league_id=78, season=2023)
    print(f"Total injury records: {len(injuries)}")

    for i, inj in enumerate(injuries[:5]):
        fixture = inj.get("fixture", {})
        team = inj.get("team", {})
        player = inj.get("player", {})
        print(f"  [{i}] fixture={fixture.get('id')} date={fixture.get('date', '')[:10]}")
        print(f"      player={player.get('name')} team={team.get('name')}")
        print(f"      type={inj.get('type')} reason={inj.get('reason')}")

    dates = Counter()
    teams = Counter()
    for inj in injuries:
        d = inj.get("fixture", {}).get("date", "")[:10]
        dates[d] += 1
        t = inj.get("team", {}).get("name", "")
        teams[t] += 1

    print(f"\nDate distribution (top 10):")
    for d, c in dates.most_common(10):
        print(f"  {d}: {c} records")

    print(f"\nTeam distribution:")
    for t, c in teams.most_common():
        print(f"  {t}: {c} records")

    await client.close()


if __name__ == "__main__":
    asyncio.run(test())
