"""Client for SportScore free live scores API (sportscore.com).

Free tier: ~10,000 requests / 24h / IP, no API key required.
Requires a visible "Powered by SportScore" dofollow backlink on pages
using the data — see https://sportscore.com/developers/terms/

Rate limits: 10,000 req/24h/IP (free tier).
At a 30-second poll interval that's 2,880 req/day — well within budget.
Key headers:
  X-RateLimit-Remaining (if sent by SportScore)
"""

from datetime import datetime
from typing import Any

from betting_bot.services.api_client import BaseAPIClient


class SportScoreClient(BaseAPIClient):
    """Client for SportScore free live scores API.

    Covers football, basketball, cricket, tennis.
    No API key needed.  10k req/24h/IP.

    **Cache is disabled by default** (``cache_enabled=False``) because
    live scores must always be fresh.  If the caller explicitly wants
    caching they can set ``use_cache=True`` per-request.
    """

    def __init__(self) -> None:
        super().__init__(
            base_url="https://sportscore.com",
            max_retries=3,
            cache_enabled=False,
            cache_ttl=0,
        )

    def _get_headers(self) -> dict[str, str]:
        return {
            "User-Agent": "BettingBot/1.0",
            "Accept": "application/json",
        }

    async def get_matches(
        self,
        sport: str = "football",
        limit: int = 10,
        use_cache: bool = False,
    ) -> dict[str, Any]:
        """Live and recent matches for a sport."""
        return await self.get(
            "api/widget/matches",
            params={"sport": sport, "limit": limit},
            use_cache=use_cache,
        )

    async def get_match_detail(
        self,
        slug: str,
        sport: str = "football",
    ) -> dict[str, Any]:
        """Single match detail by slug."""
        return await self.get(
            "api/widget/match",
            params={"sport": sport, "slug": slug},
        )

    async def get_team_fixtures(
        self,
        slug: str,
        sport: str = "football",
        limit: int = 10,
    ) -> dict[str, Any]:
        """Team's past and upcoming fixtures."""
        return await self.get(
            "api/widget/team",
            params={"sport": sport, "slug": slug, "limit": limit},
        )

    async def get_standings(
        self,
        slug: str,
        sport: str = "football",
    ) -> dict[str, Any]:
        """League / competition standings."""
        return await self.get(
            "api/widget/standings",
            params={"sport": sport, "slug": slug},
        )

    async def get_top_scorers(
        self,
        slug: str,
        sport: str = "football",
        limit: int = 10,
        stat: str = "goals",
    ) -> dict[str, Any]:
        """Top scorers for a competition."""
        return await self.get(
            "api/widget/topscorers",
            params={"sport": sport, "slug": slug, "limit": limit, "stat": stat},
        )

    async def get_player_stats(
        self,
        slug: str,
        sport: str = "football",
    ) -> dict[str, Any]:
        """Player statistics and metadata."""
        return await self.get(
            "api/widget/player",
            params={"sport": sport, "slug": slug},
        )

    async def get_bracket(
        self,
        slug: str,
        sport: str = "football",
    ) -> dict[str, Any]:
        """Knockout tournament bracket."""
        return await self.get(
            "api/widget/bracket",
            params={"sport": sport, "slug": slug},
        )

    async def get_live_tracker(
        self,
        match_id: str,
        sport: str = "football",
    ) -> dict[str, Any]:
        """Live match tracker data (position / animation)."""
        return await self.get(
            "api/widget/tracker",
            params={"sport": sport, "id": match_id},
        )

    @staticmethod
    def _extract_slug(url: str) -> str:
        """Extract the match slug from a SportScore URL.

        ``/football/match/birmingham-legion-vs-detroit-city/`` → ``birmingham-legion-vs-detroit-city``
        """
        return url.strip("/").rsplit("/", 1)[-1] if url else ""

    @staticmethod
    def _to_common_status(status: str | None) -> str:
        """Normalise SportScore status strings to short forms.

        Returns one of: ``live``, ``halftime``, ``finished``, ``scheduled``, ``postponed``, ``unknown``.
        """
        if not status:
            return "unknown"
        s = status.lower().replace(" ", "")
        if s in ("live", "inprogress"):
            return "live"
        if s in ("halftime", "ht", "break"):
            return "halftime"
        if s in ("finished", "ended", "ft"):
            return "finished"
        if s in ("pending", "scheduled", "notstarted"):
            return "scheduled"
        if s in ("postponed",):
            return "postponed"
        return "unknown"

    def parse_match_summary(self, raw: dict[str, Any]) -> dict[str, Any]:
        home_goals = raw.get("home_score")
        away_goals = raw.get("away_score")
        result = None
        if home_goals is not None and away_goals is not None:
            if home_goals > away_goals:
                result = "H"
            elif away_goals > home_goals:
                result = "A"
            else:
                result = "D"

        match_date = None
        time_str = raw.get("time", "")
        if time_str:
            try:
                match_date = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        url = raw.get("url", "")
        return {
            "external_id": self._extract_slug(url),
            "source": "sportscore",
            "match_date": match_date,
            "status": self._to_common_status(raw.get("status")),
            "status_text": raw.get("status_text"),
            "home_team_name": raw.get("home", ""),
            "away_team_name": raw.get("away", ""),
            "home_team_logo": raw.get("home_logo"),
            "away_team_logo": raw.get("away_logo"),
            "home_goals": home_goals,
            "away_goals": away_goals,
            "result": result,
        }

    def parse_match_detail(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Parse a detailed match response (from ``get_match_detail``).

        Includes score, incident list (goals, cards, subs), and live minute.
        """
        match_data = raw.get("match", {})
        summary = self.parse_match_summary(match_data)

        live_minute = match_data.get("live_minute")
        incidents = match_data.get("incidents", [])

        # Filter to goal events only
        goals = []
        for inc in incidents:
            if inc.get("is_goal") or inc.get("type_id") in (1, 8, 10):
                goals.append({
                    "minute": inc.get("time"),
                    "player": inc.get("player", ""),
                    "side": inc.get("side"),
                    "type": inc.get("type"),
                    "home_score": inc.get("home_score"),
                    "away_score": inc.get("away_score"),
                })

        summary["live_minute"] = live_minute
        summary["goals"] = goals
        summary["incidents"] = incidents
        return summary
