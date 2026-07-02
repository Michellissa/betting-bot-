"""Client for StatsBomb open data via statsbombpy."""
from datetime import datetime
from typing import Any

import pandas as pd

from betting_bot.services.api_client import BaseAPIClient


class StatsBombClient(BaseAPIClient):
    """Client for StatsBomb data.

    Uses statsbombpy under the hood. Open data requires no auth;
    paid API access requires SB_USERNAME / SB_PASSWORD env vars.
    """

    def __init__(self) -> None:
        from betting_bot.core.config import get_settings

        settings = get_settings()
        super().__init__(
            base_url="https://raw.githubusercontent.com/statsbomb/open-data/master/data",
            max_retries=2,
            cache_enabled=settings.CACHE_ENABLED,
            cache_ttl=3600,
        )

    def _get_headers(self) -> dict[str, str]:
        return {"User-Agent": "BettingBot/1.0"}

    def get_competitions(self) -> pd.DataFrame:
        """Return all available competitions as a DataFrame."""
        from statsbombpy import sb

        return sb.competitions()

    def get_matches(self, competition_id: int, season_id: int) -> pd.DataFrame:
        """Return matches for a competition/season."""
        from statsbombpy import sb

        return sb.matches(competition_id=competition_id, season_id=season_id)

    def get_lineups(self, match_id: int) -> pd.DataFrame:
        """Return lineups for a match."""
        from statsbombpy import sb

        return sb.lineups(match_id=match_id)

    def get_events(self, match_id: int) -> pd.DataFrame:
        """Return events for a match."""
        from statsbombpy import sb

        return sb.events(match_id=match_id)

    def get_competition_events(
        self, competition_id: int, season_id: int
    ) -> pd.DataFrame:
        """Return all events for a competition/season."""
        from statsbombpy import sb

        return sb.competition_events(
            competition_id=competition_id, season_id=season_id
        )

    def get_player_match_stats(self, match_id: int) -> pd.DataFrame:
        """Return player stats for a match."""
        from statsbombpy import sb

        return sb.player_match_stats(match_id=match_id)

    def parse_match_to_dict(self, row: pd.Series) -> dict[str, Any]:
        """Parse a StatsBomb match row into normalized dict."""
        match_date = row.get("match_date")
        if match_date and not isinstance(match_date, datetime):
            try:
                match_date = datetime.strptime(str(match_date), "%Y-%m-%d")
            except (ValueError, TypeError):
                match_date = None

        home_team = row.get("home_team", "")
        away_team = row.get("away_team", "")
        home_goals = row.get("home_score")
        away_goals = row.get("away_score")

        return {
            "external_id": str(row.get("match_id", "")),
            "source": "statsbomb",
            "competition_id": row.get("competition"),
            "season_id": row.get("season"),
            "competition_name": row.get("competition_name", ""),
            "season_name": row.get("season_name", ""),
            "match_date": match_date,
            "matchday": row.get("match_week", 0),
            "status": "FINISHED" if home_goals is not None else "SCHEDULED",
            "home_team_name": home_team,
            "away_team_name": away_team,
            "home_goals": home_goals,
            "away_goals": away_goals,
            "venue": row.get("stadium"),
            "home_team_manager": row.get("home_manager"),
            "away_team_manager": row.get("away_manager"),
            "result": (
                "H"
                if home_goals is not None and away_goals is not None and home_goals > away_goals
                else (
                    "A"
                    if home_goals is not None and away_goals is not None and away_goals > home_goals
                    else ("D" if home_goals is not None else None)
                )
            ),
        }
