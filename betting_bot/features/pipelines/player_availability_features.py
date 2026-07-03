"""Feature pipeline for player-level availability data (injuries, suspensions).

Uses API-Football injuries endpoint (free tier, data from April 2021+).
Queries injuries by league+season (one API call per league/season combo),
maps team names via an explicit mapping file, and stores aggregate counts
of missing players in FeatureStore.

Design constraints:
  - Uses only injury/suspension data (known days before matches)
  - Does NOT use lineup data (timing ambiguity for pre-match backtesting)
  - No per-player features (too sparse) — only team-level aggregates
  - Same NaN + imputation-with-indicator pattern as odds features
"""

from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from betting_bot.models.feature import FeatureStore
from betting_bot.models.match import Match
from betting_bot.services.api_football_client import ApiFootballClient

# Mapping: internal league name -> API-Football league ID
LEAGUE_NAME_TO_AF_ID: dict[str, int] = {
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


def _match_date_to_af_season(match_date: date) -> int:
    """Convert a match date to API-Football season year."""
    if match_date.month <= 7:
        return match_date.year - 1
    return match_date.year


MAPPING_PATH = Path("data/mappings/api_football_team_mapping.json")


def _norm(name: str) -> str:
    """Normalize a name for comparison: lowercase, no accents, no dots/hyphens."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_str = nfkd.encode("ascii", "ignore").decode("ascii")
    return ascii_str.lower().replace(".", "").replace("-", " ").replace("'", "").strip()


def _load_team_mappings() -> dict[str, dict[str, str | None]]:
    """Load the explicit API-Football team mapping file.

    Returns {league_name: {api_team_name: internal_team_name_or_null}}.
    """
    if not MAPPING_PATH.exists():
        logger.warning(f"Team mapping file not found at {MAPPING_PATH}")
        return {}
    import json
    with open(MAPPING_PATH) as f:
        mapping: dict[str, dict[str, str | None]] = json.load(f)
    _comment = mapping.pop("_comment", None)
    return mapping


def _build_reverse_map(
    league_mapping: dict[str, str | None],
) -> dict[str, str]:
    """Build {normalized_internal_name: api_name} from an {api_name: internal_name} mapping.

    Entries with null internal names are excluded (unmappable teams).
    """
    rev: dict[str, str] = {}
    for api_name, internal_name in league_mapping.items():
        if internal_name is None:
            continue
        key = _norm(internal_name)
        rev[key] = api_name
    return rev


class PlayerAvailabilityPipeline:
    """Compute player availability features for historical matches.

    Queries API-Football injuries endpoint per league+season, then
    counts missing players per team per match.

    Features produced:
      - home_missing_players_count: total missing players for home team
      - away_missing_players_count: total missing players for away team
      - player_data_available: "api_football" if data was found, else None
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._af_client = ApiFootballClient()
        self._injuries_cache: dict[str, list[dict[str, Any]]] = {}
        self._team_mappings: dict[str, dict[str, str | None]] | None = None

    def _get_team_mappings(self) -> dict[str, dict[str, str | None]]:
        if self._team_mappings is None:
            self._team_mappings = _load_team_mappings()
        return self._team_mappings

    async def _fetch_injuries_for_league_season(
        self, af_league_id: int, season: int,
    ) -> list[dict[str, Any]]:
        """Fetch injuries for a league+season from API-Football (cached in memory)."""
        key = f"{af_league_id}_{season}"
        if key in self._injuries_cache:
            return self._injuries_cache[key]

        try:
            data = await self._af_client.get_injuries(
                league_id=af_league_id, season=season
            )
        except Exception as e:
            logger.debug(
                f"Could not load injuries for AF league {af_league_id} season {season}: {e}"
            )
            data = []

        self._injuries_cache[key] = data
        logger.info(
            f"Fetched {len(data)} injury records for "
            f"API-Football league {af_league_id} season {season}"
        )
        return data

    def _lookup_api_team(
        self,
        internal_team_name: str,
        league_name: str,
        api_team_names_on_date: list[str] | None = None,
    ) -> str | None:
        """Look up the API-Football team name for a given internal DB team name.

        Uses the explicit mapping file (not fuzzy matching).
        Returns None if no mapping exists (team will be excluded).
        """
        mappings = self._get_team_mappings()
        league_mapping = mappings.get(league_name, {})
        rev = _build_reverse_map(league_mapping)
        key = _norm(internal_team_name)
        api_name = rev.get(key)
        if api_name is not None:
            return api_name
        # Fallback: check if the normalized internal name matches the normalized API name directly
        for api in api_team_names_on_date or []:
            if _norm(api) == key:
                return api
        return None

    async def backfill_all(self) -> int:
        """Compute player availability features for all finished matches.

        Returns the number of matches that received player data features.
        """
        mapping = self._get_team_mappings()
        if not mapping:
            logger.error("No team mappings loaded, cannot backfill player availability")
            return 0

        stmt = (
            select(Match)
            .options(selectinload(Match.home_team), selectinload(Match.away_team))
            .where(Match.is_finished)
            .where(Match.result.isnot(None))
            .order_by(Match.match_date)
        )
        result = await self.db.execute(stmt)
        matches: list[Match] = list(result.scalars().unique().all())
        logger.info(f"Loaded {len(matches)} finished matches from DB")

        if not matches:
            return 0

        from betting_bot.models.match import League
        league_stmt = select(League)
        league_result = await self.db.execute(league_stmt)
        leagues: list[League] = list(league_result.scalars().all())
        league_id_to_name: dict[int, str] = {league.id: league.name for league in leagues}

        league_season_matches: dict[tuple[str, int], list[Match]] = defaultdict(list)
        for match in matches:
            league_name = league_id_to_name.get(match.league_id)
            if league_name is None:
                continue
            md = match.match_date
            match_date_dt: date = md.date() if hasattr(md, "date") else md
            af_season = _match_date_to_af_season(match_date_dt)
            league_season_matches[(league_name, af_season)].append(match)

        logger.info(f"Grouped into {len(league_season_matches)} league+season groups")

        stored_count = 0
        skipped_no_league = 0
        skipped_no_data = 0
        skipped_no_mapping = 0
        unmatched_teams: set[tuple[str, str, str]] = set()  # (league, internal, api_candidates)

        for (league_name, af_season), group_matches in league_season_matches.items():
            af_league_id = LEAGUE_NAME_TO_AF_ID.get(league_name)
            if af_league_id is None:
                skipped_no_league += len(group_matches)
                continue

            injuries = await self._fetch_injuries_for_league_season(af_league_id, af_season)
            if not injuries:
                skipped_no_data += len(group_matches)
                continue

            from collections import defaultdict as dd
            injuries_by_date_team: dict[str, dict[str, list[dict]]] = dd(lambda: dd(list))
            api_teams_by_date: dict[str, list[str]] = dd(list)

            for inj in injuries:
                fixture = inj.get("fixture", {})
                fixture_date = fixture.get("date", "")
                if not fixture_date:
                    continue
                date_key = fixture_date[:10]
                team_info = inj.get("team", {})
                team_name = team_info.get("name", "")
                if not team_name:
                    continue
                team_key = _norm(team_name)
                injuries_by_date_team[date_key][team_key].append(inj)
                if team_name not in api_teams_by_date[date_key]:
                    api_teams_by_date[date_key].append(team_name)

            for match in group_matches:
                md = match.match_date
                match_date_val: date = md.date() if hasattr(md, "date") else md
                date_key = match_date_val.isoformat()

                home_team_name = match.home_team.name if match.home_team else None
                away_team_name = match.away_team.name if match.away_team else None
                if home_team_name is None or away_team_name is None:
                    skipped_no_mapping += 1
                    continue

                day_api_teams = api_teams_by_date.get(date_key, [])
                if not day_api_teams:
                    continue

                af_home = self._lookup_api_team(home_team_name, league_name, day_api_teams)
                af_away = self._lookup_api_team(away_team_name, league_name, day_api_teams)

                if af_home is None:
                    unmatched_teams.add((league_name, home_team_name, str(day_api_teams[:5])))
                if af_away is None:
                    unmatched_teams.add((league_name, away_team_name, str(day_api_teams[:5])))

                day_injuries = injuries_by_date_team.get(date_key, {})

                if af_home:
                    home_api_norm = _norm(af_home)
                    home_injuries = day_injuries.get(home_api_norm, [])
                else:
                    home_injuries = []

                if af_away:
                    away_api_norm = _norm(af_away)
                    away_injuries = day_injuries.get(away_api_norm, [])
                else:
                    away_injuries = []

                home_missing = len(home_injuries)
                away_missing = len(away_injuries)

                has_data = (home_missing > 0 or away_missing > 0)
                if not has_data:
                    continue

                repo_stmt = (
                    select(FeatureStore)
                    .where(FeatureStore.match_id == match.id)
                    .where(FeatureStore.feature_version == "v1")
                )
                fs_result = await self.db.execute(repo_stmt)
                fs = fs_result.scalar_one_or_none()

                if fs is None:
                    fs = FeatureStore(
                        match_id=match.id,
                        feature_version="v1",
                    )
                    self.db.add(fs)

                fs.home_missing_players_count = float(home_missing)
                fs.away_missing_players_count = float(away_missing)
                fs.player_data_available = "api_football"

                stored_count += 1

                if stored_count % 500 == 0:
                    await self.db.commit()
                    logger.info(f"  Progress: {stored_count} player availability features stored")

        await self.db.commit()

        if unmatched_teams:
            logger.warning(f"Unmatched teams ({len(unmatched_teams)}):")
            for ul, ut, ua in sorted(unmatched_teams):
                logger.warning(f"  [{ul}] '{ut}' not in mapping (API teams: {ua})")

        total_eligible = len(matches)
        matched_count = stored_count
        pct = (matched_count / total_eligible * 100) if total_eligible else 0
        logger.info(
            f"Player availability features stored for "
            f"{matched_count}/{total_eligible} matches ({pct:.1f}%)"
        )
        logger.info(f"  Skipped (no league mapping): {skipped_no_league}")
        logger.info(f"  Skipped (no injury data): {skipped_no_data}")
        logger.info(f"  Skipped (no team match): {skipped_no_mapping}")

        await self._af_client.close()
        return stored_count
