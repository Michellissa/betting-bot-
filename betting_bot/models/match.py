"""Database models for matches, teams, leagues, and players."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, Boolean, Numeric
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from betting_bot.database.base import Base, IntegerIDMixin, TimestampMixin


class League(IntegerIDMixin, TimestampMixin, Base):
    """Football league / competition."""

    name: Mapped[str] = MappedColumn(String(200), nullable=False)
    code: Mapped[str] = MappedColumn(String(10), unique=True, nullable=False, index=True)
    country: Mapped[str | None] = MappedColumn(String(100))
    logo_url: Mapped[str | None] = MappedColumn(String(500))
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    seasons: Mapped[list["Season"]] = relationship("Season", back_populates="league", cascade="all, delete-orphan")
    teams: Mapped[list["Team"]] = relationship("Team", back_populates="league")
    matches: Mapped[list["Match"]] = relationship("Match", back_populates="league")


class Season(IntegerIDMixin, TimestampMixin, Base):
    """A league season (e.g. 2024/2025)."""

    league_id: Mapped[int] = MappedColumn(Integer, ForeignKey("league.id"), nullable=False, index=True)
    name: Mapped[str] = MappedColumn(String(50), nullable=False)  # e.g. "2024/2025"
    start_date: Mapped[date] = MappedColumn(Date, nullable=False)
    end_date: Mapped[date] = MappedColumn(Date, nullable=False)
    is_current: Mapped[bool] = MappedColumn(Boolean, default=False)

    league: Mapped["League"] = relationship("League", back_populates="seasons")
    matches: Mapped[list["Match"]] = relationship("Match", back_populates="season")


class Team(IntegerIDMixin, TimestampMixin, Base):
    """Football team / club."""

    name: Mapped[str] = MappedColumn(String(200), nullable=False, index=True)
    short_name: Mapped[str | None] = MappedColumn(String(50))
    code: Mapped[str | None] = MappedColumn(String(10))
    country: Mapped[str | None] = MappedColumn(String(100))
    logo_url: Mapped[str | None] = MappedColumn(String(500))
    league_id: Mapped[int | None] = MappedColumn(Integer, ForeignKey("league.id"))
    stadium: Mapped[str | None] = MappedColumn(String(300))
    founded_year: Mapped[int | None] = MappedColumn(Integer)
    elo_rating: Mapped[float | None] = MappedColumn(Float, default=1500.0)

    league: Mapped["League | None"] = relationship("League", back_populates="teams")
    home_matches: Mapped[list["Match"]] = relationship(
        "Match", back_populates="home_team", foreign_keys="Match.home_team_id"
    )
    away_matches: Mapped[list["Match"]] = relationship(
        "Match", back_populates="away_team", foreign_keys="Match.away_team_id"
    )


class Match(IntegerIDMixin, TimestampMixin, Base):
    """Historical or upcoming football match."""

    league_id: Mapped[int] = MappedColumn(Integer, ForeignKey("league.id"), nullable=False, index=True)
    season_id: Mapped[int] = MappedColumn(Integer, ForeignKey("season.id"), nullable=False, index=True)
    home_team_id: Mapped[int] = MappedColumn(Integer, ForeignKey("team.id"), nullable=False, index=True)
    away_team_id: Mapped[int] = MappedColumn(Integer, ForeignKey("team.id"), nullable=False, index=True)

    match_date: Mapped[datetime] = MappedColumn(DateTime, nullable=False, index=True)
    kickoff_time: Mapped[str | None] = MappedColumn(String(20))
    round: Mapped[int | None] = MappedColumn(Integer)
    venue: Mapped[str | None] = MappedColumn(String(300))

    # Score
    home_goals: Mapped[int | None] = MappedColumn(Integer)
    away_goals: Mapped[int | None] = MappedColumn(Integer)
    home_goals_ht: Mapped[int | None] = MappedColumn(Integer)
    away_goals_ht: Mapped[int | None] = MappedColumn(Integer)

    # Result
    result: Mapped[str | None] = MappedColumn(String(1))  # H, D, A
    is_finished: Mapped[bool] = MappedColumn(Boolean, default=False)
    is_postponed: Mapped[bool] = MappedColumn(Boolean, default=False)

    # Statistics
    home_possession: Mapped[float | None] = MappedColumn(Float)
    away_possession: Mapped[float | None] = MappedColumn(Float)
    home_shots: Mapped[int | None] = MappedColumn(Integer)
    away_shots: Mapped[int | None] = MappedColumn(Integer)
    home_shots_on_target: Mapped[int | None] = MappedColumn(Integer)
    away_shots_on_target: Mapped[int | None] = MappedColumn(Integer)
    home_corners: Mapped[int | None] = MappedColumn(Integer)
    away_corners: Mapped[int | None] = MappedColumn(Integer)
    home_fouls: Mapped[int | None] = MappedColumn(Integer)
    away_fouls: Mapped[int | None] = MappedColumn(Integer)
    home_yellow_cards: Mapped[int | None] = MappedColumn(Integer)
    away_yellow_cards: Mapped[int | None] = MappedColumn(Integer)
    home_red_cards: Mapped[int | None] = MappedColumn(Integer)
    away_red_cards: Mapped[int | None] = MappedColumn(Integer)

    # xG
    home_xg: Mapped[float | None] = MappedColumn(Float)
    away_xg: Mapped[float | None] = MappedColumn(Float)

    # Expected goals against
    home_xga: Mapped[float | None] = MappedColumn(Float)
    away_xga: Mapped[float | None] = MappedColumn(Float)

    # External IDs
    external_id: Mapped[str | None] = MappedColumn(String(100), unique=True)
    source: Mapped[str | None] = MappedColumn(String(50))

    # Relationships
    league: Mapped["League"] = relationship("League", back_populates="matches")
    season: Mapped["Season"] = relationship("Season", back_populates="matches")
    home_team: Mapped["Team"] = relationship("Team", back_populates="home_matches", foreign_keys=[home_team_id])
    away_team: Mapped["Team"] = relationship("Team", back_populates="away_matches", foreign_keys=[away_team_id])


class Player(IntegerIDMixin, TimestampMixin, Base):
    """Football player."""

    name: Mapped[str] = MappedColumn(String(200), nullable=False, index=True)
    team_id: Mapped[int] = MappedColumn(Integer, ForeignKey("team.id"), nullable=False, index=True)
    position: Mapped[str | None] = MappedColumn(String(50))
    nationality: Mapped[str | None] = MappedColumn(String(100))
    date_of_birth: Mapped[date | None] = MappedColumn(Date)
    height: Mapped[int | None] = MappedColumn(Integer)
    weight: Mapped[int | None] = MappedColumn(Integer)
    external_id: Mapped[str | None] = MappedColumn(String(100), unique=True)
    is_injured: Mapped[bool] = MappedColumn(Boolean, default=False)
    is_suspended: Mapped[bool] = MappedColumn(Boolean, default=False)

    team: Mapped["Team"] = relationship("Team")


class TeamStats(IntegerIDMixin, TimestampMixin, Base):
    """Aggregated team statistics for a given season."""

    team_id: Mapped[int] = MappedColumn(Integer, ForeignKey("team.id"), nullable=False, index=True)
    season_id: Mapped[int] = MappedColumn(Integer, ForeignKey("season.id"), nullable=False, index=True)
    league_id: Mapped[int] = MappedColumn(Integer, ForeignKey("league.id"), nullable=False, index=True)

    matches_played: Mapped[int] = MappedColumn(Integer, default=0)
    wins: Mapped[int] = MappedColumn(Integer, default=0)
    draws: Mapped[int] = MappedColumn(Integer, default=0)
    losses: Mapped[int] = MappedColumn(Integer, default=0)
    goals_for: Mapped[int] = MappedColumn(Integer, default=0)
    goals_against: Mapped[int] = MappedColumn(Integer, default=0)
    goal_difference: Mapped[int] = MappedColumn(Integer, default=0)
    points: Mapped[int] = MappedColumn(Integer, default=0)
    position: Mapped[int | None] = MappedColumn(Integer)

    home_wins: Mapped[int] = MappedColumn(Integer, default=0)
    home_draws: Mapped[int] = MappedColumn(Integer, default=0)
    home_losses: Mapped[int] = MappedColumn(Integer, default=0)
    home_goals_for: Mapped[int] = MappedColumn(Integer, default=0)
    home_goals_against: Mapped[int] = MappedColumn(Integer, default=0)
    away_wins: Mapped[int] = MappedColumn(Integer, default=0)
    away_draws: Mapped[int] = MappedColumn(Integer, default=0)
    away_losses: Mapped[int] = MappedColumn(Integer, default=0)
    away_goals_for: Mapped[int] = MappedColumn(Integer, default=0)
    away_goals_against: Mapped[int] = MappedColumn(Integer, default=0)

    form_string: Mapped[str | None] = MappedColumn(String(10))

    team: Mapped["Team"] = relationship("Team")
    season: Mapped["Season"] = relationship("Season")
    league: Mapped["League"] = relationship("League")


class PlayerStats(IntegerIDMixin, TimestampMixin, Base):
    """Player statistics for a match or aggregated."""

    player_id: Mapped[int] = MappedColumn(Integer, ForeignKey("player.id"), nullable=False, index=True)
    match_id: Mapped[int | None] = MappedColumn(Integer, ForeignKey("match.id"))
    team_id: Mapped[int] = MappedColumn(Integer, ForeignKey("team.id"), nullable=False)
    season_id: Mapped[int] = MappedColumn(Integer, ForeignKey("season.id"), nullable=False, index=True)

    minutes_played: Mapped[int | None] = MappedColumn(Integer)
    goals: Mapped[int] = MappedColumn(Integer, default=0)
    assists: Mapped[int] = MappedColumn(Integer, default=0)
    shots: Mapped[int | None] = MappedColumn(Integer)
    shots_on_target: Mapped[int | None] = MappedColumn(Integer)
    passes: Mapped[int | None] = MappedColumn(Integer)
    pass_accuracy: Mapped[float | None] = MappedColumn(Float)
    tackles: Mapped[int | None] = MappedColumn(Integer)
    interceptions: Mapped[int | None] = MappedColumn(Integer)
    fouls: Mapped[int | None] = MappedColumn(Integer)
    yellow_cards: Mapped[int] = MappedColumn(Integer, default=0)
    red_cards: Mapped[int] = MappedColumn(Integer, default=0)
    rating: Mapped[float | None] = MappedColumn(Float)
    is_starter: Mapped[bool] = MappedColumn(Boolean, default=False)

    player: Mapped["Player"] = relationship("Player")
    match: Mapped["Match | None"] = relationship("Match")
    team: Mapped["Team"] = relationship("Team")
    season: Mapped["Season"] = relationship("Season")
