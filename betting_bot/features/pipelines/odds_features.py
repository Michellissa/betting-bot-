"""Feature pipeline for pre-match odds (football-data.co.uk).

Maps external CSV odds into FeatureStore columns for historical matches.
"""

import unicodedata
from datetime import date
from pathlib import Path

import pandas as pd
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from betting_bot.models.feature import FeatureStore
from betting_bot.models.match import Match
from betting_bot.services.football_data_co_uk_client import (
    FootballDataCoUkClient,
    LEAGUE_CODE_MAP,
    season_code_from_date,
)


class OddsFeaturesPipeline:
    """Compute pre-match odds features for historical matches.

    Uses cached CSV data from football-data.co.uk, maps team names
    via the explicit mapping file, and stores overround-normalized
    implied probabilities in FeatureStore.

    Usage:
        pipeline = OddsFeaturesPipeline(db)
        count = await pipeline.backfill_all()
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._fd_client = FootballDataCoUkClient()
        self._team_mappings: dict[str, dict[str, str | None]] | None = None
        self._odds_cache: dict[str, pd.DataFrame] = {}  # (league, season) -> DataFrame

    def _load_team_mappings(self) -> dict[str, dict[str, str | None]]:
        if self._team_mappings is not None:
            return self._team_mappings
        path = Path("data/mappings/football_data_co_uk_team_mapping.json")
        if not path.exists():
            logger.warning(f"Team mapping file not found at {path}")
            self._team_mappings = {}
            return self._team_mappings
        import json
        with open(path) as f:
            self._team_mappings = json.load(f)
        return self._team_mappings

    @staticmethod
    def _strip_accents(text: str) -> str:
        """Remove diacritics/accents from text for fuzzy matching."""
        nfkd = unicodedata.normalize('NFKD', text)
        return nfkd.encode('ascii', 'ignore').decode('ascii')

    def _map_team_name(
        self, fd_name: str, league: str, mapping: dict[str, dict[str, str | None]],
    ) -> str | None:
        """Map a football-data.co.uk team name to the internal name."""
        league_map = mapping.get(league)
        if league_map is None:
            return None
        internal = league_map.get(fd_name)
        return internal

    def _normalize_odds(
        self, home_odds: float, draw_odds: float, away_odds: float,
    ) -> dict[str, float]:
        """Convert decimal odds to overround-normalized implied probabilities."""
        p_home = 1.0 / home_odds
        p_draw = 1.0 / draw_odds
        p_away = 1.0 / away_odds
        total = p_home + p_draw + p_away
        return {
            "odds_home_prob": p_home / total,
            "odds_draw_prob": p_draw / total,
            "odds_away_prob": p_away / total,
            "odds_overround": total - 1.0,
            "odds_home_odds_raw": home_odds,
            "odds_draw_odds_raw": draw_odds,
            "odds_away_odds_raw": away_odds,
            "odds_source": "bet365",
        }

    def _load_odds_for_league_season(
        self, league_code: str, season_code: str,
    ) -> pd.DataFrame:
        """Load odds DataFrame for a given league and season (cached in memory)."""
        key = f"{league_code}_{season_code}"
        if key in self._odds_cache:
            return self._odds_cache[key]

        try:
            df = self._fd_client.get_odds_for_season(season_code, league_code)
        except Exception as e:
            logger.debug(f"Could not load odds for {key}: {e}")
            df = pd.DataFrame()

        self._odds_cache[key] = df
        return df

    async def backfill_all(self) -> int:
        """Compute odds features for all finished matches and store them.

        Returns the number of matches that received odds features.
        """
        mapping = self._load_team_mappings()
        if not mapping:
            logger.error("No team mappings loaded, cannot backfill odds")
            return 0

        # Load all finished matches with eager-loaded relationships
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

        # Build a map of league name -> league_id for reverse lookup on matches
        # We need to match by league name (e.g. "Premier League") to find the
        # right mapping.
        from betting_bot.models.match import League
        league_stmt = select(League)
        league_result = await self.db.execute(league_stmt)
        leagues: list[League] = list(league_result.scalars().all())
        league_id_to_name: dict[int, str] = {l.id: l.name for l in leagues}

        # Reverse mapping: internal league names -> FD league code
        # LEAGUE_CODE_MAP has {internal_name: fd_code}
        # Also build an alias for StatsBomb league names that differ
        league_name_to_fd_code: dict[str, str] = {}
        league_name_to_fd_code.update(LEAGUE_CODE_MAP)
        # Add StatsBomb-specific aliases if needed
        league_name_to_fd_code["1. Bundesliga"] = "D1"
        league_name_to_fd_code["Bundesliga"] = "D1"

        stored_count = 0
        skipped_no_odds = 0
        skipped_no_mapping = 0
        skipped_no_league = 0

        for match in matches:
            match_id = match.id
            match_date: date = match.match_date.date() if hasattr(match.match_date, 'date') else match.match_date

            league_name = league_id_to_name.get(match.league_id)
            if league_name is None:
                skipped_no_league += 1
                continue

            fd_code = league_name_to_fd_code.get(league_name)
            if fd_code is None:
                skipped_no_league += 1
                continue

            # Build season code from match date
            sc = season_code_from_date(match_date)

            # Load odds for this league/season
            odds_df = self._load_odds_for_league_season(fd_code, sc)
            if odds_df.empty:
                skipped_no_odds += 1
                continue

            # Map team names
            league_mapping = mapping.get(league_name, {})
            home_team_name = match.home_team.name if match.home_team else None
            away_team_name = match.away_team.name if match.away_team else None
            if home_team_name is None or away_team_name is None:
                skipped_no_mapping += 1
                continue

            # Reverse the mapping: internal name -> FD name (keys are FD names, values are internal)
            # Normalize accents on both sides for robust matching
            fd_by_internal = {
                self._strip_accents(v) if v else "": k
                for k, v in league_mapping.items()
            }
            fd_home = fd_by_internal.get(self._strip_accents(home_team_name))
            fd_away = fd_by_internal.get(self._strip_accents(away_team_name))
            if fd_home is None or fd_away is None:
                skipped_no_mapping += 1
                continue

            # Find matching row in odds DataFrame (FD.co.uk names)
            match_rows = odds_df[
                (odds_df["date"] == match_date)
                & (odds_df["home_team"] == fd_home)
                & (odds_df["away_team"] == fd_away)
            ]

            if match_rows.empty:
                skipped_no_odds += 1
                continue

            odds_row = match_rows.iloc[0]
            normalized = self._normalize_odds(
                odds_row["home_odds"],
                odds_row["draw_odds"],
                odds_row["away_odds"],
            )

            # Store in FeatureStore
            repo_stmt = (
                select(FeatureStore)
                .where(FeatureStore.match_id == match_id)
                .where(FeatureStore.feature_version == "v1")
            )
            fs_result = await self.db.execute(repo_stmt)
            fs = fs_result.scalar_one_or_none()

            if fs is None:
                fs = FeatureStore(
                    match_id=match_id,
                    feature_version="v1",
                )
                self.db.add(fs)

            for key, value in normalized.items():
                setattr(fs, key, value)

            stored_count += 1

            if stored_count % 500 == 0:
                await self.db.commit()
                logger.info(f"  Progress: {stored_count} odds features stored")

        await self.db.commit()
        logger.info(
            f"Odds features stored for {stored_count} matches "
            f"(no odds: {skipped_no_odds}, no mapping: {skipped_no_mapping}, "
            f"no league: {skipped_no_league})"
        )
        return stored_count
