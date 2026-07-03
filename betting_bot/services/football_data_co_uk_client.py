"""Client for Football-Data.co.uk historical CSV odds data.

This is a free, no-auth source of historical football results and betting odds.
Files are available at https://www.football-data.co.uk/mmz4281/{season}/{league}.csv
"""
import json
import time
from datetime import datetime, date
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from loguru import logger

from betting_bot.core.config import get_settings

# Directory name prefix used on football-data.co.uk (changes periodically).
# mmz4281 has been stable since ~2019. Older seasons also work under this.
FD_BASE_URL = "https://www.football-data.co.uk/mmz4281"

# League code mapping: internal league name -> football-data.co.uk league code.
# Only leagues with substantial StatsBomb match data AND available odds are listed.
LEAGUE_CODE_MAP: dict[str, str] = {
    "Premier League": "E0",
    "La Liga": "SP1",
    "Serie A": "I1",
    "Ligue 1": "F1",
    "1. Bundesliga": "D1",
    "Bundesliga": "D1",
    "Championship": "E1",
    "Eredivisie": "N1",
    "Primeira Liga": "P1",
    "Major League Soccer": "MLS",
    "Allsvenskan": "SWE",
}

# Odds columns to extract (pre-match opening odds, not closing).
# Closing columns have an additional 'C' after the bookmaker code (e.g. B365CH).
# Primary: Bet365 (most consistent historical coverage)
# Fallback: Pinnacle (sharper odds, available in most seasons)
ODDS_COLUMNS = {
    "bet365": {
        "home": "B365H",
        "draw": "B365D",
        "away": "B365A",
    },
    "pinnacle": {
        "home": "PSH",
        "draw": "PSD",
        "away": "PSA",
    },
}

# Column aliases for older seasons where Pinnacle used PH/PD/PA instead of PSH/PSD/PSA
PINNACLE_ALIASES = {
    "PH": "PSH",
    "PD": "PSD",
    "PA": "PSA",
}


def season_code_from_year(year: int) -> str:
    """Convert a year to football-data.co.uk two-digit season code.

    For European autumn-spring leagues: 2023 -> 2324
    For calendar-year leagues: the user passes the starting year.
    """
    start = year % 100
    end = (year + 1) % 100
    return f"{start:02d}{end:02d}"


def season_code_from_date(match_date: date) -> str:
    """Determine the season code for a given match date.

    European leagues: season starts in August, ends in May.
    A match in 2023-01-15 belongs to 2022/23 season -> 2223.
    A match in 2023-09-15 belongs to 2023/24 season -> 2324.
    """
    y = match_date.year
    # If match is between January and July, it belongs to previous year's autumn-start season
    if match_date.month <= 7:
        return season_code_from_year(y - 1)
    else:
        return season_code_from_year(y)


class FootballDataCoUkClient:
    """Downloads and caches CSV odds data from football-data.co.uk."""

    def __init__(self) -> None:
        settings = get_settings()
        self.cache_dir = Path("data/raw/football_data_co_uk")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BettingBot/1.0 (research project; contact michellissa@example.com)",
        })
        self._last_request_time = 0.0

    def _rate_limit(self) -> None:
        """Respect the source: minimum 1.5s between requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < 1.5:
            time.sleep(1.5 - elapsed)
        self._last_request_time = time.time()

    def _cached_path(self, season_code: str, league_code: str) -> Path:
        return self.cache_dir / season_code / f"{league_code}.csv"

    def _is_cached_current(self, path: Path, season_code: str) -> bool:
        """Check if a cached file is current enough.

        Current season (> July 2025) gets re-fetched on every call.
        Historical seasons are cached permanently.
        """
        if not path.exists():
            return False
        # Current season: re-fetch if it's the current year
        current_year = datetime.now().year
        current_season = season_code_from_year(current_year)
        if season_code == current_season:
            # Re-fetch current season every hour
            age = time.time() - path.stat().st_mtime
            return age < 3600
        return True

    def download_csv(self, season_code: str, league_code: str) -> pd.DataFrame:
        """Download a CSV from football-data.co.uk, using local cache.

        Returns a DataFrame with the raw CSV contents.
        """
        cached = self._cached_path(season_code, league_code)
        cached.parent.mkdir(parents=True, exist_ok=True)

        if self._is_cached_current(cached, season_code):
            logger.debug(f"Loading cached {season_code}/{league_code}.csv")
            try:
                return pd.read_csv(cached, encoding="latin1", on_bad_lines="skip")
            except Exception as e:
                logger.warning(f"Corrupt cache for {season_code}/{league_code}.csv, re-downloading: {e}")
                cached.unlink(missing_ok=True)

        url = f"{FD_BASE_URL}/{season_code}/{league_code}.csv"
        logger.info(f"Downloading {url}")

        self._rate_limit()
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()

        # Save to cache
        with open(cached, "wb") as f:
            f.write(resp.content)

        df = pd.read_csv(cached, encoding="latin1", on_bad_lines="skip")
        return df

    def parse_odds_row(
        self, row: pd.Series,
    ) -> dict[str, float | None]:
        """Extract pre-match odds from a CSV row.

        Returns dict with keys: home_odds, draw_odds, away_odds
        Uses Bet365 as primary, falls back to Pinnacle.

        For seasons with closing odds columns (2019/20+), the non-C columns
        are the opening/earliest snapshot - which is what we want.
        """
        result: dict[str, float | None] = {
            "home_odds": None,
            "draw_odds": None,
            "away_odds": None,
        }

        # Try Bet365 first
        b365h = row.get("B365H")
        b365d = row.get("B365D")
        b365a = row.get("B365A")

        if pd.notna(b365h) and pd.notna(b365d) and pd.notna(b365a):
            result["home_odds"] = float(b365h)
            result["draw_odds"] = float(b365d)
            result["away_odds"] = float(b365a)
            return result

        # Fallback: Pinnacle (PSH/PSD/PSA or PH/PD/PA)
        for h_col, d_col, a_col in [("PSH", "PSD", "PSA"), ("PH", "PD", "PA")]:
            psh = row.get(h_col)
            psd = row.get(d_col)
            psa = row.get(a_col)
            if pd.notna(psh) and pd.notna(psd) and pd.notna(psa):
                result["home_odds"] = float(psh)
                result["draw_odds"] = float(psd)
                result["away_odds"] = float(psa)
                return result

        return result

    def get_odds_for_season(
        self, season_code: str, league_code: str,
    ) -> pd.DataFrame:
        """Download a season CSV and return rows with parsed odds.

        Returns a DataFrame with columns:
            date, home_team, away_team, home_odds, draw_odds, away_odds
        Date is parsed to datetime.date.
        """
        df = self.download_csv(season_code, league_code)
        if df.empty:
            return df

        rows = []
        for _, row in df.iterrows():
            raw_date = row.get("Date")
            home_team = row.get("HomeTeam")
            away_team = row.get("AwayTeam")

            if pd.isna(raw_date) or pd.isna(home_team) or pd.isna(away_team):
                continue

            # Parse date (dd/mm/yy format from the CSVs)
            try:
                dt = datetime.strptime(str(raw_date).strip(), "%d/%m/%y").date()
            except (ValueError, TypeError):
                try:
                    dt = datetime.strptime(str(raw_date).strip(), "%d/%m/%Y").date()
                except (ValueError, TypeError):
                    continue

            odds = self.parse_odds_row(row)
            if odds["home_odds"] is None:
                continue

            rows.append({
                "date": dt,
                "home_team": str(home_team).strip(),
                "away_team": str(away_team).strip(),
                "home_odds": odds["home_odds"],
                "draw_odds": odds["draw_odds"],
                "away_odds": odds["away_odds"],
                "season_code": season_code,
                "league_code": league_code,
            })

        return pd.DataFrame(rows)

    def normalize_implied_prob(
        self, home_odds: float, draw_odds: float, away_odds: float,
    ) -> dict[str, float]:
        """Convert decimal odds to implied probabilities, removing overround.

        Returns dict with keys: home_prob, draw_prob, away_prob, overround
        The three probs are normalized to sum to 1.0.
        """
        p_home = 1.0 / home_odds
        p_draw = 1.0 / draw_odds
        p_away = 1.0 / away_odds
        total = p_home + p_draw + p_away
        overround = total - 1.0

        return {
            "home_prob": p_home / total,
            "draw_prob": p_draw / total,
            "away_prob": p_away / total,
            "overround": overround,
            "home_prob_raw": p_home,
            "draw_prob_raw": p_draw,
            "away_prob_raw": p_away,
        }

    def get_odds_for_leagues(
        self,
        league_mapping: dict[str, str],
        date_ranges: dict[str, tuple[date, date]],
    ) -> pd.DataFrame:
        """Download odds for multiple leagues across relevant seasons.

        Args:
            league_mapping: {internal_league_name: fd_league_code}
            date_ranges: {internal_league_name: (min_date, max_date)}

        Returns:
            DataFrame with all odds data, with added 'internal_league' column.
        """
        all_odds = []

        for internal_name, fd_code in league_mapping.items():
            if internal_name not in date_ranges:
                logger.warning(f"No date range for {internal_name}, skipping")
                continue

            min_date, max_date = date_ranges[internal_name]
            min_year = min_date.year
            max_year = max_date.year

            # Generate season codes that could overlap with our date range
            seasons_needed = set()
            for y in range(min_year - 1, max_year + 2):
                sc = season_code_from_year(y)
                seasons_needed.add(sc)

            logger.info(f"Fetching odds for {internal_name} ({fd_code}), "
                        f"seasons: {min_year}-{max_year}")

            for sc in sorted(seasons_needed):
                try:
                    odds_df = self.get_odds_for_season(sc, fd_code)
                    if odds_df.empty:
                        logger.debug(f"  No data for {fd_code}/{sc}")
                        continue

                    # Filter to date range of interest
                    odds_df = odds_df[
                        (odds_df["date"] >= min_date) & (odds_df["date"] <= max_date)
                    ]
                    if odds_df.empty:
                        continue

                    odds_df["internal_league"] = internal_name
                    all_odds.append(odds_df)
                    logger.info(f"  {fd_code}/{sc}: {len(odds_df)} rows")

                except Exception as e:
                    logger.warning(f"  Failed {fd_code}/{sc}: {e}")

            # Rate limit between leagues
            self._rate_limit()

        if all_odds:
            return pd.concat(all_odds, ignore_index=True)
        return pd.DataFrame()
