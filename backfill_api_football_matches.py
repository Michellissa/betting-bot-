"""Backfill 2022-2024 match data from API-Football for PL/La Liga/Serie A.

Free tier covers seasons 2022-2024 only (not 2021).
Uses existing data_orchestrator patterns: dedup by external_id, source tagging.
"""

import asyncio
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.database.repositories.league_repository import LeagueRepository, SeasonRepository
from betting_bot.database.repositories.match_repository import MatchRepository, TeamRepository
from betting_bot.database.session import get_async_session
from betting_bot.models.match import League, Team
from betting_bot.services.api_football_client import ApiFootballClient

TARGETS: dict[str, dict[str, Any]] = {
    "PL": {"af_id": 39, "db_code": "PL", "name": "Premier League"},
    "PD": {"af_id": 140, "db_code": "PD", "name": "La Liga"},
    "SA": {"af_id": 135, "db_code": "SA", "name": "Serie A"},
}
SEASONS = [2022, 2023, 2024]

MAPPING_PATH = Path("data/mappings/api_football_team_mapping.json")


def _load_mappings() -> dict[str, dict[str, str | None]]:
    if MAPPING_PATH.exists():
        with open(MAPPING_PATH) as f:
            m: dict = json.load(f)
        m.pop("_comment", None)
        return m
    return {}


def _save_mappings(mappings: dict[str, dict[str, str | None]]) -> None:
    sorted_m = dict(sorted(mappings.items()))
    with open(MAPPING_PATH, "w") as f:
        json.dump({"_comment": "Maps API-Football team names to internal DB team names.", **sorted_m}, f, indent=2)
    logger.info(f"Updated mapping file at {MAPPING_PATH}")


def _norm(name: str) -> str:
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return ascii_str.lower().replace(".", "").replace("-", " ").replace("'", "").replace("\u00e1", "a").replace("\u00e9", "e").replace("\u00ed", "i").replace("\u00f3", "o").replace("\u00fa", "u").replace("\u00f1", "n").strip()


def _find_team_id(teams: list[Team], api_name: str, mapping: dict[str, str | None]) -> int | None:
    """Find the best matching existing team. Returns team.id or None."""
    norm_api = _norm(api_name)

    # 1. Exact match
    for t in teams:
        if t.name == api_name:
            return t.id

    # 2. Mapping lookup
    mapped = mapping.get(api_name)
    if mapped is not None:
        for t in teams:
            if t.name == mapped:
                return t.id

    # 3. Normalized match
    for t in teams:
        if _norm(t.name) == norm_api:
            return t.id

    return None


async def _get_or_create_season(db: AsyncSession, league_id: int, season_year: int) -> int:
    """Find or create a season record for API-Football season year format."""
    season_repo = SeasonRepository(db)
    season_name = f"{season_year}/{season_year + 1}"
    existing = await season_repo.get_by(league_id=league_id, name=season_name)
    if existing:
        return existing.id

    # Check if any season overlaps this date range
    from datetime import date
    start = date(season_year, 8, 1)
    end = date(season_year + 1, 7, 31)
    seasons = await season_repo.get_by_league(league_id)
    for s in seasons:
        if s.start_date <= start and s.end_date >= end:
            return s.id

    season = await season_repo.create(
        league_id=league_id,
        name=season_name,
        start_date=start,
        end_date=end,
        is_current=(season_year == 2024),
    )
    return season.id


async def backfill_league_season(
    db: AsyncSession,
    af_client: ApiFootballClient,
    af_league_id: int,
    league_model: League,
    season: int,
    mappings: dict[str, dict[str, str | None]],
    league_map_key: str,
) -> dict[str, Any]:
    """Backfill matches for one league+season. Returns stats dict."""
    stats: dict[str, Any] = {
        "fetched": 0, "stored": 0, "skipped_dup": 0,
        "teams_created": 0, "teams_matched": 0,
    }

    logger.info(f"Fetching {league_model.name} season {season} (AF ID {af_league_id})...")
    fixtures = await af_client.get_fixtures(
        league_id=af_league_id, season=season, limit=500,
    )
    stats["fetched"] = len(fixtures)
    if not fixtures:
        return stats

    match_repo = MatchRepository(db)
    team_repo = TeamRepository(db)
    season_id = await _get_or_create_season(db, league_model.id, season)

    # Pre-load all existing teams for this league
    all_teams = await team_repo.get_by_league(league_model.id)
    league_mapping = mappings.get(league_map_key, {})
    new_mapping_entries: dict[str, str | None] = {}

    for raw in fixtures:
        parsed = af_client.parse_fixture(raw)

        # Dedup by external_id
        existing = await match_repo.get_by(external_id=parsed["external_id"])
        if existing:
            stats["skipped_dup"] += 1
            continue

        # Find or create home team
        home_api_name = parsed["home_team_name"]
        home_id = _find_team_id(all_teams, home_api_name, league_mapping)
        if home_id is None:
            home_team = await team_repo.create(
                name=home_api_name,
                league_id=league_model.id,
                elo_rating=1500.0,
            )
            all_teams.append(home_team)
            home_id = home_team.id
            stats["teams_created"] += 1
            if home_api_name not in league_mapping:
                new_mapping_entries[home_api_name] = home_api_name
        else:
            stats["teams_matched"] += 1

        # Find or create away team
        away_api_name = parsed["away_team_name"]
        away_id = _find_team_id(all_teams, away_api_name, league_mapping)
        if away_id is None:
            away_team = await team_repo.create(
                name=away_api_name,
                league_id=league_model.id,
                elo_rating=1500.0,
            )
            all_teams.append(away_team)
            away_id = away_team.id
            stats["teams_created"] += 1
            if away_api_name not in league_mapping:
                new_mapping_entries[away_api_name] = away_api_name
        else:
            stats["teams_matched"] += 1

        match_date = parsed.get("match_date")
        home_goals = parsed.get("home_goals")
        away_goals = parsed.get("away_goals")
        is_finished = (home_goals is not None)
        result = parsed.get("result")

        await match_repo.create(
            league_id=league_model.id,
            season_id=season_id,
            home_team_id=home_id,
            away_team_id=away_id,
            match_date=match_date or datetime.now(),
            round=parsed.get("round"),
            venue=parsed.get("venue"),
            home_goals=home_goals,
            away_goals=away_goals,
            home_goals_ht=parsed.get("home_goals_ht"),
            away_goals_ht=parsed.get("away_goals_ht"),
            result=result,
            is_finished=is_finished,
            external_id=parsed["external_id"],
            source="api_football",
        )
        stats["stored"] += 1

    # Update mapping for new teams
    if new_mapping_entries:
        if league_map_key not in mappings:
            mappings[league_map_key] = {}
        mappings[league_map_key].update(new_mapping_entries)
        logger.info(f"  Added {len(new_mapping_entries)} new mapping entries for {league_map_key}")

    return stats


async def main():
    af_client = ApiFootballClient()
    mappings = _load_mappings()
    all_stats: dict[str, dict] = defaultdict(dict)

    async for db in get_async_session():
        league_repo = LeagueRepository(db)

        for league_code, target in TARGETS.items():
            league_model = await league_repo.get_by_code(target["db_code"])
            if not league_model:
                league_model = await league_repo.get_by(name=target["name"])
            if not league_model:
                logger.warning(f"League {target['name']} ({target['db_code']}) not found in DB")
                continue

            map_key = target["name"]
            for season in SEASONS:
                stats = await backfill_league_season(
                    db, af_client, target["af_id"],
                    league_model, season, mappings, map_key,
                )
                all_stats[f"{league_code}/{season}"] = stats
                await db.commit()

    await af_client.close()

    # Save updated mappings
    _save_mappings(mappings)

    # Report
    print("\n" + "=" * 60)
    print("BACKFILL RESULTS")
    print("=" * 60)
    total_stored = 0
    total_fetched = 0
    for key, s in sorted(all_stats.items()):
        print(f"  {key}: fetched={s['fetched']}, stored={s['stored']}, dup_skip={s['skipped_dup']}, teams_created={s['teams_created']}")
        total_stored += s["stored"]
        total_fetched += s["fetched"]
    print("-" * 60)
    print(f"  TOTAL: fetched={total_fetched}, stored={total_stored} new matches")


if __name__ == "__main__":
    asyncio.run(main())
