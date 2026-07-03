"""Client for The Odds API (the-odds-api.com)."""

from datetime import date, datetime
from typing import Any

from loguru import logger

from betting_bot.core.config import get_settings
from betting_bot.services.api_client import BaseAPIClient, RateLimitConfig

SPORT_KEY_MAP = {
    "PL": "soccer_epl",
    "PD": "soccer_spain_la_liga",
    "SA": "soccer_italy_serie_a",
    "BL1": "soccer_germany_bundesliga",
    "FL1": "soccer_france_ligue_one",
    "CL": "soccer_uefa_champs_league",
    "ELC": "soccer_england_championship",
    "DED": "soccer_netherlands_eredivisie",
    "PPL": "soccer_portugal_primeira_liga",
    "FIFA WORLD": "soccer_fifa_world_cup",
}

# Team name mapping from our DB (WC26 / StatsBomb) to The Odds API names
ODDS_API_TEAM_MAP = {
    "United States": "USA",
    "Cape Verde Islands": "Cape Verde",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "German DR": "East Germany",
    "Czechoslovakia": "Czechoslovakia",
}

REGIONS = ["uk", "eu", "us"]
MARKETS = ["h2h", "totals", "btts"]


class OddsAPIClient(BaseAPIClient):
    """Client for The Odds API."""

    def __init__(self) -> None:
        settings = get_settings()
        super().__init__(
            api_key=settings.ODDS_API_KEY,
            base_url="https://api.the-odds-api.com/v4",
            max_retries=3,
            rate_limit=RateLimitConfig(requests_per_minute=30, requests_per_day=500),
            cache_enabled=settings.CACHE_ENABLED,
            cache_ttl=settings.CACHE_TTL // 2,
        )

    def _get_headers(self) -> dict[str, str]:
        return {}

    async def get_sports(self) -> list[dict[str, Any]]:
        """Get all available sports."""
        data = await self.get("sports", params={"apiKey": self.api_key})
        return data if isinstance(data, list) else []

    async def get_odds(
        self,
        sport_key: str = "soccer_epl",
        regions: str = "uk",
        markets: str = "h2h,totals,btts",
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get odds for upcoming matches."""
        params: dict[str, Any] = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "oddsFormat": "decimal",
            "dateFormat": "iso",
            "bookmakers": "auto",
        }
        if date_from:
            params["commenceTimeFrom"] = date_from.isoformat()
        if date_to:
            params["commenceTimeTo"] = date_to.isoformat()

        data = await self.get(f"sports/{sport_key}/odds", params=params)
        return data[:limit] if isinstance(data, list) else []

    async def get_scores(
        self,
        sport_key: str = "soccer_epl",
        days_from: int = 1,
        date_from: date | None = None,
    ) -> list[dict[str, Any]]:
        """Get scores for completed matches."""
        params: dict[str, Any] = {
            "apiKey": self.api_key,
            "daysFrom": days_from,
            "dateFormat": "iso",
        }
        if date_from:
            params["commenceTimeFrom"] = date_from.isoformat()

        data = await self.get(f"sports/{sport_key}/scores", params=params)
        return data if isinstance(data, list) else []

    async def get_events(
        self, sport_key: str = "soccer_epl", date_from: date | None = None
    ) -> list[dict[str, Any]]:
        """Get upcoming events for a sport."""
        params: dict[str, Any] = {"apiKey": self.api_key}
        if date_from:
            params["commenceTimeFrom"] = date_from.isoformat()
        data = await self.get(f"sports/{sport_key}/events", params=params)
        return data if isinstance(data, list) else []

    def parse_odds(self, raw: dict[str, Any]) -> list[dict[str, Any]]:
        """Parse raw odds data into normalized format."""
        parsed = []
        home_team = raw.get("home_team", "")
        away_team = raw.get("away_team", "")
        commence_time = raw.get("commence_time", "")

        try:
            match_date = datetime.fromisoformat(commence_time.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            match_date = None

        for bookmaker in raw.get("bookmakers", []):
            bookmaker_name = bookmaker.get("title", "")
            entry = {
                "external_match_id": raw.get("id"),
                "home_team": home_team,
                "away_team": away_team,
                "match_date": match_date,
                "bookmaker": bookmaker_name,
                "source": "odds_api",
                "timestamp": datetime.utcnow(),
            }

            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                outcomes = market.get("outcomes", [])

                if market_key == "h2h":
                    for outcome in outcomes:
                        name = outcome.get("name", "")
                        price = outcome.get("price")
                        if name == home_team:
                            entry["home_odds"] = price
                        elif name == away_team:
                            entry["away_odds"] = price
                        elif name in ("Draw", "Tie"):
                            entry["draw_odds"] = price

                elif market_key == "totals":
                    for outcome in outcomes:
                        point = outcome.get("point")
                        price = outcome.get("price")
                        name = outcome.get("name", "")
                        if point == 2.5:
                            if name == "Over":
                                entry["over_2_5_odds"] = price
                            elif name == "Under":
                                entry["under_2_5_odds"] = price

                elif market_key == "btts":
                    for outcome in outcomes:
                        name = outcome.get("name", "")
                        price = outcome.get("price")
                        if name == "Yes":
                            entry["btts_yes_odds"] = price
                        elif name == "No":
                            entry["btts_no_odds"] = price

            if "home_odds" in entry:
                parsed.append(entry)

        return parsed
