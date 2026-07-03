"""Discover API-Football league IDs."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sys, io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from betting_bot.services.api_football_client import ApiFootballClient


async def main():
    client = ApiFootballClient()
    leagues = await client.get_leagues()
    # Search for leagues matching our DB leagues
    search_terms = ["Women", "NWSL", "Liga F", "Frauen", "Indian Super", "Allsvenskan",
                    "MLS", "Major League", "Primeira", "Eredivisie", "Championship",
                    "Brasileirao", "Argentina"]
    for league in leagues:
        l = league.get("league", {})
        name = l.get("name", "")
        lid = l.get("id")
        le_type = l.get("type", "")
        for term in search_terms:
            if term.lower() in name.lower() and le_type == "League":
                print(f"  {lid:5d} | {name:40s} | {le_type}")
                break
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
