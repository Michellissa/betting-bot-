"""Client for the free World Cup 2026 API (worldcup26.ir)."""

from datetime import datetime
from typing import Any

from betting_bot.services.api_client import BaseAPIClient


class WorldCup2026Client(BaseAPIClient):
    """Client for World Cup 2026 free REST API.

    No API key required.  Covers all 104 matches, 48 teams, 12 groups,
    16 stadiums.  See https://worldcup26.ir/api-docs
    """

    def __init__(self) -> None:
        super().__init__(
            base_url="https://worldcup26.ir",
            max_retries=3,
            cache_enabled=True,
            cache_ttl=300,
        )

    def _get_headers(self) -> dict[str, str]:
        return {"User-Agent": "BettingBot/1.0"}

    async def get_games(self) -> list[dict[str, Any]]:
        raw = await self.get("get/games")
        return raw.get("games", [])

    async def get_groups(self) -> list[dict[str, Any]]:
        raw = await self.get("get/groups")
        return raw.get("groups", [])

    async def get_teams(self) -> list[dict[str, Any]]:
        raw = await self.get("get/teams")
        return raw.get("teams", [])

    async def get_stadiums(self) -> list[dict[str, Any]]:
        raw = await self.get("get/stadiums")
        return raw.get("stadiums", [])

    async def get_group_standings(self, group_name: str) -> list[dict[str, Any]]:
        groups = await self.get_groups()
        for g in groups:
            if g.get("name") == group_name.upper():
                return g.get("teams", [])
        return []

    async def get_team_games(self, team_id: str | int) -> list[dict[str, Any]]:
        games = await self.get_games()
        tid = str(team_id)
        return [g for g in games if g.get("home_team_id") == tid or g.get("away_team_id") == tid]

    def parse_game(self, raw: dict[str, Any]) -> dict[str, Any]:
        home_goals = raw.get("home_score")
        away_goals = raw.get("away_score")
        result = None
        if home_goals is not None and away_goals is not None:
            home_goals = int(home_goals) if home_goals else 0
            away_goals = int(away_goals) if away_goals else 0
            if home_goals > away_goals:
                result = "H"
            elif away_goals > home_goals:
                result = "A"
            else:
                result = "D"

        match_date = None
        date_str = raw.get("local_date", "")
        if date_str:
            try:
                match_date = datetime.strptime(date_str, "%m/%d/%Y %H:%M")
            except (ValueError, TypeError):
                pass

        return {
            "external_id": raw.get("id", ""),
            "source": "worldcup2026",
            "competition": "FIFA World Cup 2026",
            "group": raw.get("group"),
            "matchday": raw.get("matchday"),
            "stage": raw.get("type", "group"),
            "match_date": match_date,
            "status": "FINISHED" if raw.get("finished") == "TRUE" else "SCHEDULED",
            "home_team_name": raw.get("home_team_name_en", ""),
            "away_team_name": raw.get("away_team_name_en", ""),
            "home_team_id": raw.get("home_team_id"),
            "away_team_id": raw.get("away_team_id"),
            "home_goals": int(home_goals) if home_goals is not None else None,
            "away_goals": int(away_goals) if away_goals is not None else None,
            "home_scorers": raw.get("home_scorers"),
            "away_scorers": raw.get("away_scorers"),
            "result": result,
            "stadium_id": raw.get("stadium_id"),
            "time_elapsed": raw.get("time_elapsed"),
        }
