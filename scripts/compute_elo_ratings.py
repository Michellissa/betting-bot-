"""Compute persistent Elo ratings using canonical team IDs.

Problem (fixed): The same real-world team (e.g. FC Barcelona) previously had
separate Team rows for each league (La Liga, Champions League, Copa del Rey),
each with its own Elo rating. This meant Barcelona's UCL performance never
affected their La Liga Elo, and vice versa.

Fix: Uses data/mappings/canonical_team_crosswalk.json to merge all per-league
Team entries for the same real-world team into one canonical identity per pool.
After each match, the canonical Elo is propagated to ALL per-league Team rows.

Pools: Club and international are computed in separate passes with separate
rating pools (no Elo leak between them). International matches use neutral
venue (no home advantage bonus).

Usage:
    python -m scripts.compute_elo_ratings
"""
import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from loguru import logger

from betting_bot.database.session import get_async_session
from betting_bot.models.match import Match, Team
from betting_bot.services.elo import EloRating

# Path to crosswalk files
CROSSWALK_PATH = Path("data/mappings/canonical_team_crosswalk.json")
ID_LOOKUP_PATH = Path("data/mappings/team_id_to_canonical_name.json")


async def compute_elo_for_pool(
    db,
    pool_name: str,
    match_rows: list,
    crosswalk: dict,
    id_to_canonical: dict[str, str],
) -> int:
    """Compute Elo for one pool (club or international).

    Args:
        pool_name: "club" or "international"
        match_rows: list of (Match, is_neutral) tuples, sorted chronologically
        crosswalk: canonical name -> pool -> data
        id_to_canonical: team_id -> canonical name

    Returns:
        Number of team rows updated
    """
    elo_system = EloRating(k_factor=32.0, home_advantage=100.0)
    # Track ONE Elo per canonical team within this pool
    canonical_elo: dict[str, float] = {}
    updated = 0

    for match, is_neutral in match_rows:
        home_tid = str(match.home_team_id)
        away_tid = str(match.away_team_id)

        # id_to_canonical has string keys (from JSON)
        home_canon = id_to_canonical.get(home_tid)
        away_canon = id_to_canonical.get(away_tid)
        if not home_canon or not away_canon:
            continue

        # Verify both teams belong to this pool
        h_info = crosswalk.get(home_canon, {}).get(pool_name)
        a_info = crosswalk.get(away_canon, {}).get(pool_name)
        if not h_info or not a_info:
            # Team exists but not in this pool — skip silently
            # (e.g., a club match that somehow references an int'l team ID)
            continue

        home_rating = canonical_elo.get(home_canon, 1500.0)
        away_rating = canonical_elo.get(away_canon, 1500.0)

        result_data = elo_system.update(
            home_rating,
            away_rating,
            match.home_goals or 0,
            match.away_goals or 0,
            is_neutral=is_neutral,
        )

        canonical_elo[home_canon] = result_data.home_elo_after
        canonical_elo[away_canon] = result_data.away_elo_after

        # Propagate to ALL per-league Team rows for this canonical team
        for tid in h_info["team_ids"]:
            team = await db.get(Team, tid)
            if team is not None:
                team.elo_rating = result_data.home_elo_after
                updated += 1
        for tid in a_info["team_ids"]:
            team = await db.get(Team, tid)
            if team is not None:
                team.elo_rating = result_data.away_elo_after
                updated += 1

    logger.info(
        f"  {pool_name} pool: {len(canonical_elo)} canonical teams, "
        f"top 3: {sorted(canonical_elo.items(), key=lambda x: -x[1])[:3]}"
    )
    return updated


async def compute_all_elo():
    """Iterate all finished matches chronologically per pool."""
    # Load crosswalk
    with open(CROSSWALK_PATH, encoding="utf-8") as f:
        crosswalk = json.load(f)
    with open(ID_LOOKUP_PATH, encoding="utf-8") as f:
        id_to_canonical = json.load(f)

    logger.info(f"Loaded crosswalk: {len(crosswalk)} canonical names")
    logger.info(f"Loaded ID lookup: {len(id_to_canonical)} team IDs")

    # Build international team ID set from the crosswalk
    intl_team_ids: set[int] = set()
    for name, pools in crosswalk.items():
        if "international" in pools:
            intl_team_ids.update(pools["international"]["team_ids"])

    async for db in get_async_session():
        # Load all finished matches chronologically
        result = await db.execute(
            select(Match)
            .where(Match.is_finished)
            .where(Match.home_goals.isnot(None))
            .where(Match.away_goals.isnot(None))
            .where(Match.result.isnot(None))
            .order_by(Match.match_date)
        )
        all_matches = result.scalars().all()
        logger.info(f"Processing {len(all_matches)} finished matches")

        # Split matches into club and international pools
        club_matches = []
        intl_matches = []
        for m in all_matches:
            # A match is international if BOTH teams are international teams
            is_intl = (
                m.home_team_id in intl_team_ids
                and m.away_team_id in intl_team_ids
            )
            if is_intl:
                intl_matches.append((m, True))  # neutral venue
            else:
                club_matches.append((m, False))  # home advantage applies

        logger.info(f"  Club matches: {len(club_matches)}")
        logger.info(f"  International matches: {len(intl_matches)}")

        # Compute club pool
        logger.info("Computing club Elo pool...")
        club_updated = await compute_elo_for_pool(
            db, "club", club_matches, crosswalk, id_to_canonical
        )

        # Compute international pool (separate, starting from 1500)
        logger.info("Computing international Elo pool...")
        intl_updated = await compute_elo_for_pool(
            db, "international", intl_matches, crosswalk, id_to_canonical
        )

        await db.commit()
        logger.info(f"Updated {club_updated + intl_updated} team rows "
                     f"(club: {club_updated}, intl: {intl_updated})")

        # Display top teams by pool
        for pool_name in ("club", "international"):
            logger.info(f"Top {pool_name} teams by Elo:")
            result = await db.execute(
                select(Team).order_by(Team.elo_rating.desc()).limit(30)
            )
            teams_with_pool = []
            for t in result.scalars().all():
                can_name = id_to_canonical.get(str(t.id), t.name)
                pools = crosswalk.get(can_name, {})
                if pool_name in pools:
                    teams_with_pool.append((can_name, t.elo_rating))
            # Deduplicate (same canonical team may appear via multiple Team rows)
            seen = set()
            for name, elo in teams_with_pool:
                if name not in seen:
                    logger.info(f"    {name:30s} {elo:>8.1f}")
                    seen.add(name)
                if len(seen) >= 15:
                    break


if __name__ == "__main__":
    asyncio.run(compute_all_elo())
