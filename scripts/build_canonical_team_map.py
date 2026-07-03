"""Build canonical team crosswalk for Elo computation.

Problem: The same real-world team (e.g. FC Barcelona) has separate Team rows
for each league it appears in (La Liga, Champions League, Copa del Rey).
A team's Elo rating should be shared across ALL leagues within its pool.

Pool detection: Uses an explicit list of international-competition league codes,
since the League.country field is unreliable (e.g. UEFA Euro and Champions League
both have country='Europe' but one is national teams, the other clubs).

Cross-pool contamination: A team name appearing in both club AND international
pools (e.g. 'Argentina' in Copa America + FIFA World Cup) is actually the same
Argentina national team in two different international tournaments — NOT the
same name spanning club and international. Our pool detection must correctly
classify ALL international competitions as 'international' to prevent this.

The output crosswalk maps: canonical_name -> { pool -> { team_ids, leagues } }

Usage: python -m scripts.build_canonical_team_map
"""
import asyncio
import json
from pathlib import Path

from sqlalchemy import select, func
from loguru import logger

from betting_bot.database.session import get_async_session
from betting_bot.models.match import Team, League, Match

# Explicit list: all leagues that are national-team (not club) competitions.
# Detected by checking the competition type, not the country field.
# UEFA Champions League (clubs) and UEFA Euro (national teams) both have
# country='Europe' — only the explicit list below correctly distinguishes them.
INTERNATIONAL_LEAGUE_CODES = {
    "FIFA WORLD",     # FIFA World Cup (men's)
    "AFRICAN CU",     # African Cup of Nations
    "COPA AMERI",     # Copa America
    "FIFA U20 W",     # FIFA U20 World Cup
    "UEFA EURO",      # UEFA European Championship (men's)
    "UEFA WOMEN",     # UEFA Women's European Championship
    "WOMEN'S WO",     # FIFA Women's World Cup
}


def _is_international_league(league_code: str) -> bool:
    return league_code in INTERNATIONAL_LEAGUE_CODES


async def build():
    logger.info("Building canonical team crosswalk...")
    async for db in get_async_session():
        # Get all teams with their league info
        result = await db.execute(
            select(Team, League)
            .join(League, Team.league_id == League.id)
            .order_by(Team.name)
        )
        all_rows = result.all()

        teams_by_name: dict[str, list[dict]] = {}
        for team, league in all_rows:
            name = team.name
            if name not in teams_by_name:
                teams_by_name[name] = []
            mc = await db.scalar(
                select(func.count(Match.id))
                .where((Match.home_team_id == team.id) | (Match.away_team_id == team.id))
            )
            is_intl = _is_international_league(league.code.strip())
            teams_by_name[name].append({
                "team_id": team.id,
                "league_id": league.id,
                "league_code": league.code.strip(),
                "league_name": league.name,
                "is_international": is_intl,
                "match_count": mc or 0,
            })

        # Build crosswalk: canonical name -> pool -> team_ids
        crosswalk = {}
        for name, entries in teams_by_name.items():
            club_entries = [e for e in entries if not e["is_international"]]
            intl_entries = [e for e in entries if e["is_international"]]

            pools = {}
            if club_entries:
                pools["club"] = {
                    "team_ids": [e["team_id"] for e in club_entries],
                    "leagues": list(set(e["league_code"] for e in club_entries)),
                    "total_matches": sum(e["match_count"] for e in club_entries),
                }
            if intl_entries:
                pools["international"] = {
                    "team_ids": [e["team_id"] for e in intl_entries],
                    "leagues": list(set(e["league_code"] for e in intl_entries)),
                    "total_matches": sum(e["match_count"] for e in intl_entries),
                }
            if pools:
                crosswalk[name] = pools

        # Summary
        total_names = len(crosswalk)
        multi_entry = sum(1 for v in crosswalk.values() if sum(len(p["team_ids"]) for p in v.values()) > 1)
        cross_pool = sum(1 for v in crosswalk.values() if len(v) > 1)
        total_team_rows = sum(sum(len(p["team_ids"]) for p in v.values()) for v in crosswalk.values())

        logger.info(f"Total unique team names: {total_names}")
        logger.info(f"  Single-entry names: {total_names - multi_entry}")
        logger.info(f"  Multi-entry names (canonical merge needed): {multi_entry}")
        logger.info(f"  Cross-pool names (club + intl): {cross_pool}")
        logger.info(f"  Total underlying Team rows: {total_team_rows}")

        if cross_pool > 0:
            logger.warning("Cross-pool names found (should be 0 with correct detection):")
            for name, pools in sorted(crosswalk.items()):
                if len(pools) > 1:
                    logger.warning(f"  {name}: club({pools['club']['team_ids']} in {pools['club']['leagues']}) "
                                   f"intl({pools['international']['team_ids']} in {pools['international']['leagues']})")

        # Save crosswalk
        output = Path("data/mappings/canonical_team_crosswalk.json")
        with open(output, "w", encoding="utf-8") as f:
            json.dump(crosswalk, f, indent=2, sort_keys=True, ensure_ascii=False)
        logger.info(f"Saved crosswalk to {output} (total names: {total_names})")

        # Also save a simple ID lookup: team_id -> canonical name
        id_to_name = {}
        for name, pools in crosswalk.items():
            for pool_data in pools.values():
                for tid in pool_data["team_ids"]:
                    id_to_name[str(tid)] = name
        id_output = Path("data/mappings/team_id_to_canonical_name.json")
        with open(id_output, "w", encoding="utf-8") as f:
            json.dump(id_to_name, f, indent=2, sort_keys=True)
        logger.info(f"Saved ID-to-canonical lookup to {id_output}")


if __name__ == "__main__":
    asyncio.run(build())
