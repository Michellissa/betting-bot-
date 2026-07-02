"""Orchestrator for fetching data from multiple API sources."""

from datetime import date, datetime
from typing import Any

import pandas as pd
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.core.constants import League
from betting_bot.database.repositories.league_repository import LeagueRepository
from betting_bot.database.repositories.match_repository import MatchRepository, TeamRepository
from betting_bot.database.repositories.odds_repository import BookmakerRepository, OddsRepository
from betting_bot.models.match import League as LeagueModel
from betting_bot.models.match import Team
from betting_bot.services.api_football_client import ApiFootballClient
from betting_bot.services.fifa_player_client import FIFAPlayerClient
from betting_bot.services.football_data_client import FootballDataClient
from betting_bot.services.odds_api_client import OddsAPIClient
from betting_bot.services.sportscore_client import SportScoreClient
from betting_bot.services.statsbomb_client import StatsBombClient
from betting_bot.services.worldcup2026_client import WorldCup2026Client


class DataOrchestrator:
    """Coordinates data fetching from multiple sources."""

    def __init__(self) -> None:
        self.football_data = FootballDataClient()
        self.api_football = ApiFootballClient()
        self.odds_api = OddsAPIClient()
        self.statsbomb = StatsBombClient()
        self.fifa_players = FIFAPlayerClient()
        self.worldcup = WorldCup2026Client()
        self.sportscore = SportScoreClient()

    async def close_all(self) -> None:
        """Close all API clients."""
        await self.football_data.close()
        await self.api_football.close()
        await self.odds_api.close()

    async def fetch_and_store_matches(
        self,
        db: AsyncSession,
        league_code: str | None = None,
        days_back: int = 30,  # noqa: ARG002
        days_forward: int = 7,  # noqa: ARG002
    ) -> int:
        """Fetch matches from primary source and store in database.

        Returns count of matches stored.
        """
        league_repo = LeagueRepository(db)
        match_repo = MatchRepository(db)
        team_repo = TeamRepository(db)

        date_from = date.today().replace(day=1)
        date_to = date.today()

        leagues_to_fetch = (
            [league_code] if league_code else [lg.value for lg in League]
        )

        total_stored = 0

        for code in leagues_to_fetch:
            try:
                raw_matches = await self.football_data.get_matches(
                    league_code=code,
                    date_from=date_from,
                    date_to=date_to,
                    limit=100,
                )
            except Exception as e:
                logger.warning(f"Failed to fetch {code} from football-data: {e}")
                continue

            league_model = await league_repo.get_by_code(code)
            if not league_model:
                logger.warning(f"League {code} not found in database, skipping")
                continue

            for raw in raw_matches:
                parsed = self.football_data.parse_match(raw)
                stored = await self._store_match(
                    db, match_repo, team_repo, league_model, parsed
                )
                if stored:
                    total_stored += 1

        await db.commit()
        logger.info(f"Stored {total_stored} matches from football-data.org")
        return total_stored

    async def fetch_and_store_odds(
        self,
        db: AsyncSession,
        league_code: str | None = None,
    ) -> int:
        """Fetch odds from The Odds API and store in database."""

        odds_repo = OddsRepository(db)
        bookmaker_repo = BookmakerRepository(db)
        match_repo = MatchRepository(db)

        sport_key = "soccer_epl"
        if league_code:
            from betting_bot.services.odds_api_client import SPORT_KEY_MAP

            sport_key = SPORT_KEY_MAP.get(league_code, sport_key)

        try:
            raw_odds = await self.odds_api.get_odds(sport_key=sport_key)
        except Exception as e:
            logger.warning(f"Failed to fetch odds for {sport_key}: {e}")
            return 0

        total_stored = 0
        for raw_event in raw_odds:
            parsed_odds_list = self.odds_api.parse_odds(raw_event)
            home_team_name = raw_event.get("home_team", "")

            match = await match_repo.search_by_team_name(home_team_name, limit=1)
            if not match:
                continue

            match_obj = match[0]
            for odds_entry in parsed_odds_list:
                bookmaker_name = odds_entry.get("bookmaker", "Unknown")
                bookmaker = await bookmaker_repo.get_by_name(bookmaker_name)
                if not bookmaker:
                    bookmaker = await bookmaker_repo.create(name=bookmaker_name)

                existing = await odds_repo.get_by(
                    match_id=match_obj.id,
                    bookmaker_id=bookmaker.id,
                )
                if not existing:
                    await odds_repo.create(
                        match_id=match_obj.id,
                        bookmaker_id=bookmaker.id,
                        home_odds=odds_entry.get("home_odds"),
                        draw_odds=odds_entry.get("draw_odds"),
                        away_odds=odds_entry.get("away_odds"),
                        over_2_5_odds=odds_entry.get("over_2_5_odds"),
                        under_2_5_odds=odds_entry.get("under_2_5_odds"),
                        btts_yes_odds=odds_entry.get("btts_yes_odds"),
                        btts_no_odds=odds_entry.get("btts_no_odds"),
                        odds_timestamp=datetime.utcnow(),
                        source="odds_api",
                    )
                    total_stored += 1

        await db.commit()
        logger.info(f"Stored {total_stored} odds entries")
        return total_stored

    async def _store_match(
        self,
        db: AsyncSession,
        match_repo: MatchRepository,
        team_repo: TeamRepository,
        league_model: LeagueModel,
        parsed: dict[str, Any],
    ) -> bool:
        """Store a parsed match in the database."""
        if not parsed.get("match_date"):
            return False

        existing = await match_repo.get_by(external_id=parsed["external_id"])
        if existing:
            return False

        home_team = await team_repo.get_by(
            name=parsed["home_team_name"], league_id=league_model.id
        )
        away_team = await team_repo.get_by(
            name=parsed["away_team_name"], league_id=league_model.id
        )

        if not home_team or not away_team:
            home_team = await self._ensure_team(team_repo, league_model, parsed["home_team_name"])
            away_team = await self._ensure_team(team_repo, league_model, parsed["away_team_name"])

        season = await self._get_or_create_season(db, league_model, parsed)

        is_finished = parsed.get("status") in ("FINISHED", "FT")
        home_goals = parsed.get("home_goals")
        away_goals = parsed.get("away_goals")

        await match_repo.create(
            league_id=league_model.id,
            season_id=season.id if season else 1,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            match_date=parsed["match_date"],
            round=parsed.get("matchday"),
            venue=parsed.get("venue"),
            home_goals=home_goals,
            away_goals=away_goals,
            home_goals_ht=parsed.get("home_goals_ht"),
            away_goals_ht=parsed.get("away_goals_ht"),
            result=parsed.get("result"),
            is_finished=is_finished,
            external_id=parsed["external_id"],
            source=parsed["source"],
        )
        return True

    async def _ensure_team(
        self,
        team_repo: TeamRepository,
        league: LeagueModel,
        team_name: str,
    ) -> Team:
        """Find or create a team."""
        existing = await team_repo.get_by(name=team_name, league_id=league.id)
        if existing:
            return existing
        return await team_repo.create(
            name=team_name,
            league_id=league.id,
            country=league.country,
            elo_rating=1500.0,
        )

    async def _get_or_create_season(
        self,
        db: AsyncSession,
        league: LeagueModel,
        parsed: dict[str, Any],
    ) -> Any:
        """Find or create the appropriate season for a match."""
        from betting_bot.database.repositories.league_repository import SeasonRepository

        season_repo = SeasonRepository(db)
        season_name = parsed.get("season_name", "")

        if season_name:
            existing = await season_repo.get_by(
                league_id=league.id, name=season_name
            )
            if existing:
                return existing

        match_date = parsed.get("match_date")
        if match_date:
            seasons = await season_repo.get_by_league(league.id)
            for season in seasons:
                if season.start_date <= match_date.date() <= season.end_date:
                    return season

        return await season_repo.get_by(league_id=league.id, is_current=True)

    async def fetch_statsbomb_data(
        self,
        db: AsyncSession,
        competition_id: int | None = None,
        season_id: int | None = None,
    ) -> int:
        """Fetch matches from StatsBomb open data and store in database."""
        from betting_bot.database.repositories.league_repository import SeasonRepository

        match_repo = MatchRepository(db)
        team_repo = TeamRepository(db)
        league_repo = LeagueRepository(db)
        season_repo = SeasonRepository(db)

        comps = self.statsbomb.get_competitions()
        if competition_id is not None and season_id is not None:
            comps = comps[
                (comps["competition_id"] == competition_id)
                & (comps["season_id"] == season_id)
            ]
        if comps.empty:
            logger.warning("No StatsBomb competitions matched")
            return 0

        total_stored = 0
        for _, comp_row in comps.iterrows():
            cid = comp_row["competition_id"]
            sid = comp_row["season_id"]
            comp_name = comp_row["competition_name"]
            country = comp_row.get("country_name", "Unknown")

            # Find or create league
            league_model = await league_repo.get_by_code(comp_name)
            if not league_model:
                league_model = await league_repo.get_by(name=comp_name)
            if not league_model:
                league_model = await league_repo.create(
                    name=comp_name,
                    code=comp_name[:10].upper(),
                    country=country,
                    is_active=True,
                )
                logger.info(f"Created new league: {comp_name} ({country})")

            # Find or create season
            from datetime import date

            season_name = comp_row.get("season_name", str(sid))
            season_model = await season_repo.get_by(
                league_id=league_model.id, name=season_name
            )
            if not season_model:
                season_start = comp_row.get("season_start")
                season_end = comp_row.get("season_end")
                _isna = isinstance(season_start, float) and pd.isna(season_start)
                if season_start is None or _isna:
                    season_start = date(int(sid) if isinstance(sid, (int, float)) else 2020, 1, 1)
                _isna_end = isinstance(season_end, float) and pd.isna(season_end)
                if season_end is None or _isna_end:
                    season_end = date(
                        (int(sid) + 1) if isinstance(sid, (int, float)) else 2021, 1, 1
                    )
                season_model = await season_repo.create(
                    league_id=league_model.id,
                    name=season_name,
                    start_date=season_start,
                    end_date=season_end,
                    is_current=False,
                )

            try:
                matches_df = self.statsbomb.get_matches(cid, sid)
            except Exception as e:
                logger.warning(f"Failed to get StatsBomb matches for {comp_name}: {e}")
                continue

            for _, match_row in matches_df.iterrows():
                parsed = self.statsbomb.parse_match_to_dict(match_row)
                parsed["season_name"] = season_name
                stored = await self._store_match(
                    db, match_repo, team_repo, league_model, parsed
                )
                if stored:
                    total_stored += 1

        await db.commit()
        logger.info(f"Stored {total_stored} matches from StatsBomb")
        return total_stored

    async def fetch_worldcup_data(self) -> int:
        """Fetch World Cup 2026 data."""
        try:
            games = await self.worldcup.get_games()
            logger.info(f"Fetched {len(games)} World Cup 2026 matches")
            return len(games)
        except Exception as e:
            logger.warning(f"Failed to fetch World Cup data: {e}")
            return 0

    async def fetch_and_store_all(
        self,
        db: AsyncSession,
        league_code: str | None = None,
        days_back: int = 30,
        days_forward: int = 7,
        source: str = "all",
    ) -> dict[str, int]:
        """Fetch from all available sources.

        Args:
            source: "all", "football_data", "statsbomb", "odds", "fifa"
        Returns dict of source -> count stored.
        """
        results: dict[str, int] = {}

        if source in ("all", "football_data"):
            logger.info("Fetching from football-data.org...")
            results["football_data"] = await self.fetch_and_store_matches(
                db, league_code=league_code, days_back=days_back, days_forward=days_forward
            )

        if source in ("all", "statsbomb"):
            logger.info("Fetching from StatsBomb open data...")
            results["statsbomb"] = await self.fetch_statsbomb_data(db)

        if source in ("all", "odds"):
            logger.info("Fetching from Odds API...")
            results["odds"] = await self.fetch_and_store_odds(
                db, league_code=league_code
            )

        if source in ("all", "fifa"):
            logger.info("Loading FIFA player data...")
            try:
                df = self.fifa_players.load()
                results["fifa"] = len(df)
            except FileNotFoundError as e:
                logger.warning(f"FIFA data unavailable: {e}")
                results["fifa"] = 0

        if source in ("all", "worldcup"):
            logger.info("Fetching World Cup 2026 data...")
            results["worldcup"] = await self.fetch_worldcup_data()

        return results
