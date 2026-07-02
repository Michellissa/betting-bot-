"""Database models for odds from various bookmakers."""

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Boolean, Numeric
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from betting_bot.database.base import Base, IntegerIDMixin, TimestampMixin


class Bookmaker(IntegerIDMixin, TimestampMixin, Base):
    """Bookmaker / sportsbook."""

    name: Mapped[str] = MappedColumn(String(100), unique=True, nullable=False, index=True)
    short_name: Mapped[str | None] = MappedColumn(String(20))
    logo_url: Mapped[str | None] = MappedColumn(String(500))
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)
    country: Mapped[str | None] = MappedColumn(String(100))

    odds: Mapped[list["Odds"]] = relationship("Odds", back_populates="bookmaker", cascade="all, delete-orphan")


class Odds(IntegerIDMixin, TimestampMixin, Base):
    """Odds for a specific match from a specific bookmaker."""

    match_id: Mapped[int] = MappedColumn(Integer, ForeignKey("match.id"), nullable=False, index=True)
    bookmaker_id: Mapped[int] = MappedColumn(Integer, ForeignKey("bookmaker.id"), nullable=False, index=True)

    # 1X2 odds
    home_odds: Mapped[float | None] = MappedColumn(Float)
    draw_odds: Mapped[float | None] = MappedColumn(Float)
    away_odds: Mapped[float | None] = MappedColumn(Float)

    # Over/Under odds
    over_2_5_odds: Mapped[float | None] = MappedColumn(Float)
    under_2_5_odds: Mapped[float | None] = MappedColumn(Float)
    over_1_5_odds: Mapped[float | None] = MappedColumn(Float)
    under_1_5_odds: Mapped[float | None] = MappedColumn(Float)
    over_3_5_odds: Mapped[float | None] = MappedColumn(Float)
    under_3_5_odds: Mapped[float | None] = MappedColumn(Float)

    # Both Teams To Score odds
    btts_yes_odds: Mapped[float | None] = MappedColumn(Float)
    btts_no_odds: Mapped[float | None] = MappedColumn(Float)

    # Double Chance
    home_or_draw_odds: Mapped[float | None] = MappedColumn(Float)
    home_or_away_odds: Mapped[float | None] = MappedColumn(Float)
    draw_or_away_odds: Mapped[float | None] = MappedColumn(Float)

    # Additional info
    is_live: Mapped[bool] = MappedColumn(Boolean, default=False)
    is_opening: Mapped[bool] = MappedColumn(Boolean, default=False)
    is_closing: Mapped[bool] = MappedColumn(Boolean, default=False)
    odds_timestamp: Mapped[datetime] = MappedColumn(DateTime, nullable=False)
    source: Mapped[str | None] = MappedColumn(String(50))

    # Relationships
    match: Mapped["Match"] = relationship("Match")
    bookmaker: Mapped["Bookmaker"] = relationship("Bookmaker", back_populates="odds")


class OddsHistory(IntegerIDMixin, TimestampMixin, Base):
    """Historical odds movements for a match."""

    match_id: Mapped[int] = MappedColumn(Integer, ForeignKey("match.id"), nullable=False, index=True)
    bookmaker_id: Mapped[int] = MappedColumn(Integer, ForeignKey("bookmaker.id"), nullable=False, index=True)

    home_odds: Mapped[float] = MappedColumn(Float)
    draw_odds: Mapped[float] = MappedColumn(Float)
    away_odds: Mapped[float] = MappedColumn(Float)
    recorded_at: Mapped[datetime] = MappedColumn(DateTime, nullable=False, index=True)

    match: Mapped["Match"] = relationship("Match")
    bookmaker: Mapped["Bookmaker"] = relationship("Bookmaker")
