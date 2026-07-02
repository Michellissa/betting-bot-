"""Client for football-data.org API (free tier: 10 req/min)."""

from datetime import date, datetime
from typing import Any

from loguru import logger

from betting_bot.core.config import get_settings
from betting_bot.core.constants import League, MatchResult
from betting_bot.core.exceptions import APIError
from betting_bot.services.api_client import BaseAPIClient, RateLimitConfig

LEAGUE_CODE_MAP = {
    "PL": "PL",
    "PD": "PD",
    "SA": "SA",
    "BL1": "BL1",
    "FL1": "FL1",
    "CL": "CL",
    "ELC": "ELC",
    "DED": "DED",
    "PPL": "PPL",
}


class FootballDataClient(BaseAPIClient):
    """Client for football-data.org API."""

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            api_key=settings.FOOTBALL_DATA_API_KEY,
            base_url="https://api.football-data.org/v4",
            max_retries=3,
            rate_limit=RateLimitConfig(requests_per_minute=10, requests_per_day=1000),
            cache_enabled=settings.CACHE_ENABLED,
            cache_ttl=settings.CACHE_TTL,
        )

    def _get_headers(self) -> dict[str, str]:
        return {"X-Auth-Token": self.api_key}

    async def get_competitions(self) -> list[dict[str, Any]]:
        """Get all available competitions."""
        data = await self.get("competitions")
        return data.get("competitions", [])

    async def get_competition(self, league_code: str) -> dict[str, Any]:
        """Get a specific competition."""
        mapped = LEAGUE_CODE_MAP.get(league_code, league_code)
        return await self.get(f"competitions/{mapped}")

    async def get_standings(self, league_code: str) -> dict[str, Any]:
        """Get current standings for a league."""
        mapped = LEAGUE_CODE_MAP.get(league_code, league_code)
        return await self.get(f"competitions/{mapped}/standings")

    async def get_matches(
        self,
        league_code: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get matches with optional filters."""
        params: dict[str, Any] = {"limit": min(limit, 100)}
        if date_from:
            params["dateFrom"] = date_from.isoformat()
        if date_to:
            params["dateTo"] = date_to.isoformat()
        if status:
            params["status"] = status

        if league_code:
            mapped = LEAGUE_CODE_MAP.get(league_code, league_code)
            data = await self.get(f"competitions/{mapped}/matches", params=params)
        else:
            data = await self.get("matches", params=params)

        return data.get("matches", [])

    async def get_match(self, match_id: int) -> dict[str, Any]:
        """Get a single match by ID."""
        return await self.get(f"matches/{match_id}")

    async def get_team(self, team_id: int) -> dict[str, Any]:
        """Get team information."""
        return await self.get(f"teams/{team_id}")

    async def get_team_matches(
        self,
        team_id: int,
        limit: int = 100,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get matches for a specific team."""
        params: dict[str, Any] = {"limit": min(limit, 100)}
        if status:
            params["status"] = status
        data = await self.get(f"teams/{team_id}/matches", params=params)
        return data.get("matches", [])

    async def get_players(self, team_id: int) -> list[dict[str, Any]]:
        """Get squad for a team."""
        data = await self.get(f"teams/{team_id}")
        return data.get("squad", [])

    def parse_match(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Parse raw API match data into normalized format."""
        score = raw.get("score", {})
        full_time = score.get("fullTime", {})
        half_time = score.get("halfTime", {})
        home_team = raw.get("homeTeam", {})
        away_team = raw.get("awayTeam", {})
        competition = raw.get("competition", {})
        season = raw.get("season", {})

        home_goals = full_time.get("home")
        away_goals = full_time.get("away")

        result = None
        if home_goals is not None and away_goals is not None:
            result = MatchResult.from_score(home_goals, away_goals).value

        match_date_str = raw.get("utcDate", raw.get("matchday", ""))
        try:
            match_date = datetime.fromisoformat(match_date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            match_date = None

        return {
            "external_id": str(raw.get("id")),
            "source": "football_data",
            "competition_code": competition.get("code"),
            "competition_name": competition.get("name"),
            "season_name": season.get("name", ""),
            "season_start": season.get("startDate"),
            "season_end": season.get("endDate"),
            "match_date": match_date,
            "matchday": raw.get("matchday"),
            "status": raw.get("status"),
            "home_team_name": home_team.get("name"),
            "home_team_id": str(home_team.get("id")),
            "away_team_name": away_team.get("name"),
            "away_team_id": str(away_team.get("id")),
            "home_goals": home_goals,
            "away_goals": away_goals,
            "home_goals_ht": half_time.get("home"),
            "away_goals_ht": half_time.get("away"),
            "result": result,
            "venue": raw.get("venue"),
            "referee": self._get_referee(raw),
        }

    def _get_referee(self, raw: dict[str, Any]) -> str | None:
        """Extract referee name from match data."""
        referees = raw.get("referees", [])
        if referees:
            return referees[0].get("name")
        return None
