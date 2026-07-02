"""Client for API-Football (api-sports.io / rapidapi)."""

from datetime import date, datetime
from typing import Any

from loguru import logger

from betting_bot.core.config import get_settings
from betting_bot.core.constants import MatchResult
from betting_bot.core.exceptions import APIError
from betting_bot.services.api_client import BaseAPIClient, RateLimitConfig

LEAGUE_IDS = {
    "PL": 39,
    "PD": 140,
    "SA": 135,
    "BL1": 78,
    "FL1": 61,
    "CL": 2,
    "ELC": 40,
    "DED": 88,
    "PPL": 94,
}


class ApiFootballClient(BaseAPIClient):
    """Client for API-Football (api-sports.io)."""

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            api_key=settings.API_FOOTBALL_KEY,
            base_url=f"https://{settings.API_FOOTBALL_HOST}",
            max_retries=3,
            rate_limit=RateLimitConfig(requests_per_minute=30, requests_per_day=10000),
            cache_enabled=settings.CACHE_ENABLED,
            cache_ttl=settings.CACHE_TTL,
        )

    def _get_headers(self) -> dict[str, str]:
        settings = get_settings()
        return {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": settings.API_FOOTBALL_HOST,
        }

    async def get_leagues(self) -> list[dict[str, Any]]:
        """Get all available leagues."""
        data = await self.get("leagues")
        return data.get("response", [])

    async def get_league_info(self, league_id: int) -> dict[str, Any]:
        """Get information about a specific league."""
        data = await self.get("leagues", params={"id": league_id})
        results = data.get("response", [])
        return results[0] if results else {}

    async def get_seasons(self) -> list[int]:
        """Get all available seasons."""
        data = await self.get("leagues/seasons")
        return data.get("response", [])

    async def get_teams(self, league_id: int, season: int) -> list[dict[str, Any]]:
        """Get all teams in a league for a season."""
        data = await self.get(
            "teams", params={"league": league_id, "season": season}
        )
        return data.get("response", [])

    async def get_standings(self, league_id: int, season: int) -> list[dict[str, Any]]:
        """Get league standings."""
        data = await self.get(
            "standings", params={"league": league_id, "season": season}
        )
        results = data.get("response", [])
        if results:
            standings = results[0].get("league", {}).get("standings", [])
            return standings[0] if standings else []
        return []

    async def get_fixtures(
        self,
        league_id: int | None = None,
        season: int | None = None,
        team_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        status: str | None = None,
        live: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get fixtures/matches with filters."""
        params: dict[str, Any] = {}
        if league_id:
            params["league"] = league_id
        if season:
            params["season"] = season
        if team_id:
            params["team"] = team_id
        if date_from:
            params["from"] = date_from.isoformat()
        if date_to:
            params["to"] = date_to.isoformat()
        if status:
            params["status"] = status
        if live:
            params["live"] = live

        data = await self.get("fixtures", params=params)
        return data.get("response", [])[:limit]

    async def get_fixture(self, fixture_id: int) -> dict[str, Any]:
        """Get a single fixture by ID."""
        data = await self.get("fixtures", params={"id": fixture_id})
        results = data.get("response", [])
        return results[0] if results else {}

    async def get_fixture_statistics(self, fixture_id: int) -> list[dict[str, Any]]:
        """Get statistics for a fixture."""
        data = await self.get(
            "fixtures/statistics", params={"fixture": fixture_id}
        )
        return data.get("response", [])

    async def get_fixture_events(self, fixture_id: int) -> list[dict[str, Any]]:
        """Get events (goals, cards, subs) for a fixture."""
        data = await self.get(
            "fixtures/events", params={"fixture": fixture_id}
        )
        return data.get("response", [])

    async def get_fixture_lineups(self, fixture_id: int) -> list[dict[str, Any]]:
        """Get lineups for a fixture."""
        data = await self.get(
            "fixtures/lineups", params={"fixture": fixture_id}
        )
        return data.get("response", [])

    async def get_head_to_head(self, team1_id: int, team2_id: int, limit: int = 10) -> list[dict[str, Any]]:
        """Get head-to-head fixtures between two teams."""
        data = await self.get(
            "fixtures/headtohead",
            params={"h2h": f"{team1_id}-{team2_id}", "last": limit},
        )
        return data.get("response", [])

    async def get_team_statistics(
        self, league_id: int, season: int, team_id: int
    ) -> dict[str, Any]:
        """Get team statistics for a season."""
        data = await self.get(
            "teams/statistics",
            params={"league": league_id, "season": season, "team": team_id},
        )
        results = data.get("response", [])
        return results[0] if results else {}

    async def get_players(
        self,
        team_id: int,
        season: int,
        league_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get players for a team."""
        data = await self.get(
            "players",
            params={"team": team_id, "season": season, "league": league_id},
        )
        return data.get("response", [])

    async def get_injuries(
        self,
        league_id: int | None = None,
        season: int | None = None,
        team_id: int | None = None,
        fixture_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get injury data."""
        params: dict[str, Any] = {}
        if league_id:
            params["league"] = league_id
        if season:
            params["season"] = season
        if team_id:
            params["team"] = team_id
        if fixture_id:
            params["fixture"] = fixture_id
        data = await self.get("injuries", params=params)
        return data.get("response", [])

    async def get_predictions(self, fixture_id: int) -> dict[str, Any]:
        """Get API-Football predictions for a fixture."""
        data = await self.get("predictions", params={"fixture": fixture_id})
        results = data.get("response", [])
        return results[0] if results else {}

    def parse_fixture(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Parse raw API fixture data into normalized format."""
        fixture = raw.get("fixture", {})
        league = raw.get("league", {})
        teams = raw.get("teams", {})
        goals = raw.get("goals", {})
        score = raw.get("score", {})

        home_team = teams.get("home", {})
        away_team = teams.get("away", {})

        home_goals = goals.get("home")
        away_goals = goals.get("away")

        result = None
        if home_goals is not None and away_goals is not None:
            result = MatchResult.from_score(int(home_goals), int(away_goals)).value

        match_date_str = fixture.get("date", "")
        try:
            match_date = datetime.fromisoformat(match_date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            match_date = None

        status = fixture.get("status", {})
        venue = fixture.get("venue", {})

        return {
            "external_id": str(fixture.get("id")),
            "source": "api_football",
            "league_id": league.get("id"),
            "league_name": league.get("name"),
            "league_country": league.get("country"),
            "season": league.get("season"),
            "round": league.get("round"),
            "match_date": match_date,
            "timestamp": fixture.get("timestamp"),
            "status": status.get("long"),
            "status_short": status.get("short"),
            "home_team_name": home_team.get("name"),
            "home_team_id": str(home_team.get("id")),
            "away_team_name": away_team.get("name"),
            "away_team_id": str(away_team.get("id")),
            "home_goals": int(home_goals) if home_goals is not None else None,
            "away_goals": int(away_goals) if away_goals is not None else None,
            "home_goals_ht": self._get_ht_score(score, "home"),
            "away_goals_ht": self._get_ht_score(score, "away"),
            "result": result,
            "venue": venue.get("name"),
            "city": venue.get("city"),
            "referee": fixture.get("referee"),
        }

    def _get_ht_score(self, score: dict[str, Any], side: str) -> int | None:
        """Extract half-time score."""
        ht = score.get("halftime", {})
        val = ht.get(side)
        return int(val) if val is not None else None

    def parse_statistics(self, raw: list[dict[str, Any]]) -> dict[str, Any]:
        """Parse fixture statistics into a flat dict."""
        stats = {}
        for team_stats in raw:
            team = team_stats.get("team", {})
            prefix = "home" if team.get("id") else "away"
            for stat in team_stats.get("statistics", []):
                name = stat.get("type", "").lower().replace(" ", "_")
                value = stat.get("value")
                stats[f"{prefix}_{name}"] = value
        return stats
