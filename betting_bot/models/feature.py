"""Database models for feature definitions and feature store."""

from sqlalchemy import Float, ForeignKey, Integer, String, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from betting_bot.database.base import Base, IntegerIDMixin, TimestampMixin


class FeatureDefinition(IntegerIDMixin, TimestampMixin, Base):
    """Metadata about available features."""

    name: Mapped[str] = MappedColumn(String(200), unique=True, nullable=False, index=True)
    category: Mapped[str] = MappedColumn(String(50), nullable=False)
    description: Mapped[str | None] = MappedColumn(Text)
    data_type: Mapped[str] = MappedColumn(String(50), nullable=False)
    source: Mapped[str | None] = MappedColumn(String(100))
    transformation: Mapped[str | None] = MappedColumn(String(200))
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)
    version_added: Mapped[str | None] = MappedColumn(String(20))
    dependencies: Mapped[dict | None] = MappedColumn(JSON)


class FeatureStore(IntegerIDMixin, TimestampMixin, Base):
    """Computed feature values for each match."""

    match_id: Mapped[int] = MappedColumn(Integer, ForeignKey("match.id"), nullable=False, index=True)
    feature_version: Mapped[str] = MappedColumn(String(20), nullable=False, index=True)

    # Form features
    home_form_last_5: Mapped[float | None] = MappedColumn(Float)
    away_form_last_5: Mapped[float | None] = MappedColumn(Float)
    home_form_last_10: Mapped[float | None] = MappedColumn(Float)
    away_form_last_10: Mapped[float | None] = MappedColumn(Float)
    home_points_last_5: Mapped[float | None] = MappedColumn(Float)
    away_points_last_5: Mapped[float | None] = MappedColumn(Float)
    home_points_last_10: Mapped[float | None] = MappedColumn(Float)
    away_points_last_10: Mapped[float | None] = MappedColumn(Float)
    home_form_trend: Mapped[float | None] = MappedColumn(Float)
    away_form_trend: Mapped[float | None] = MappedColumn(Float)

    # Goal features
    home_goals_scored_avg_5: Mapped[float | None] = MappedColumn(Float)
    home_goals_conceded_avg_5: Mapped[float | None] = MappedColumn(Float)
    away_goals_scored_avg_5: Mapped[float | None] = MappedColumn(Float)
    away_goals_conceded_avg_5: Mapped[float | None] = MappedColumn(Float)
    home_goals_scored_avg_10: Mapped[float | None] = MappedColumn(Float)
    home_goals_conceded_avg_10: Mapped[float | None] = MappedColumn(Float)
    away_goals_scored_avg_10: Mapped[float | None] = MappedColumn(Float)
    away_goals_conceded_avg_10: Mapped[float | None] = MappedColumn(Float)
    home_goal_diff_avg_5: Mapped[float | None] = MappedColumn(Float)
    away_goal_diff_avg_5: Mapped[float | None] = MappedColumn(Float)
    home_goal_diff_avg_10: Mapped[float | None] = MappedColumn(Float)
    away_goal_diff_avg_10: Mapped[float | None] = MappedColumn(Float)
    home_scoring_streak: Mapped[float | None] = MappedColumn(Float)
    away_scoring_streak: Mapped[float | None] = MappedColumn(Float)
    home_clean_sheet_rate_5: Mapped[float | None] = MappedColumn(Float)
    away_clean_sheet_rate_5: Mapped[float | None] = MappedColumn(Float)
    home_clean_sheet_rate_10: Mapped[float | None] = MappedColumn(Float)
    away_clean_sheet_rate_10: Mapped[float | None] = MappedColumn(Float)

    # xG features
    home_xg_avg_5: Mapped[float | None] = MappedColumn(Float)
    away_xg_avg_5: Mapped[float | None] = MappedColumn(Float)
    home_xga_avg_5: Mapped[float | None] = MappedColumn(Float)
    away_xga_avg_5: Mapped[float | None] = MappedColumn(Float)
    home_xg_avg_10: Mapped[float | None] = MappedColumn(Float)
    away_xg_avg_10: Mapped[float | None] = MappedColumn(Float)
    home_xga_avg_10: Mapped[float | None] = MappedColumn(Float)
    away_xga_avg_10: Mapped[float | None] = MappedColumn(Float)
    home_xg_diff_5: Mapped[float | None] = MappedColumn(Float)
    away_xg_diff_5: Mapped[float | None] = MappedColumn(Float)
    home_xg_diff_10: Mapped[float | None] = MappedColumn(Float)
    away_xg_diff_10: Mapped[float | None] = MappedColumn(Float)

    # Elo features
    home_elo: Mapped[float | None] = MappedColumn(Float)
    away_elo: Mapped[float | None] = MappedColumn(Float)
    elo_diff: Mapped[float | None] = MappedColumn(Float)
    home_elo_probability: Mapped[float | None] = MappedColumn(Float)

    # Head-to-head features
    h2h_home_wins: Mapped[int | None] = MappedColumn(Integer)
    h2h_draws: Mapped[int | None] = MappedColumn(Integer)
    h2h_away_wins: Mapped[int | None] = MappedColumn(Integer)
    h2h_home_goals_avg: Mapped[float | None] = MappedColumn(Float)
    h2h_away_goals_avg: Mapped[float | None] = MappedColumn(Float)
    h2h_matches_played: Mapped[int | None] = MappedColumn(Integer)
    h2h_home_win_rate: Mapped[float | None] = MappedColumn(Float)
    h2h_away_win_rate: Mapped[float | None] = MappedColumn(Float)
    h2h_over_2_5_rate: Mapped[float | None] = MappedColumn(Float)
    h2h_btts_rate: Mapped[float | None] = MappedColumn(Float)

    # Possession
    home_possession_avg_5: Mapped[float | None] = MappedColumn(Float)
    away_possession_avg_5: Mapped[float | None] = MappedColumn(Float)
    home_possession_avg_10: Mapped[float | None] = MappedColumn(Float)
    away_possession_avg_10: Mapped[float | None] = MappedColumn(Float)

    # Shot features
    home_shots_avg_5: Mapped[float | None] = MappedColumn(Float)
    away_shots_avg_5: Mapped[float | None] = MappedColumn(Float)
    home_shots_on_target_avg_5: Mapped[float | None] = MappedColumn(Float)
    away_shots_on_target_avg_5: Mapped[float | None] = MappedColumn(Float)
    home_shots_avg_10: Mapped[float | None] = MappedColumn(Float)
    away_shots_avg_10: Mapped[float | None] = MappedColumn(Float)
    home_shots_on_target_avg_10: Mapped[float | None] = MappedColumn(Float)
    away_shots_on_target_avg_10: Mapped[float | None] = MappedColumn(Float)

    # Corner features
    home_corners_avg_5: Mapped[float | None] = MappedColumn(Float)
    away_corners_avg_5: Mapped[float | None] = MappedColumn(Float)
    home_corners_avg_10: Mapped[float | None] = MappedColumn(Float)
    away_corners_avg_10: Mapped[float | None] = MappedColumn(Float)

    # Discipline features
    home_fouls_avg_5: Mapped[float | None] = MappedColumn(Float)
    away_fouls_avg_5: Mapped[float | None] = MappedColumn(Float)
    home_yellow_cards_avg_5: Mapped[float | None] = MappedColumn(Float)
    away_yellow_cards_avg_5: Mapped[float | None] = MappedColumn(Float)

    # Rest and travel
    home_rest_days: Mapped[float | None] = MappedColumn(Float)
    away_rest_days: Mapped[float | None] = MappedColumn(Float)
    travel_distance: Mapped[float | None] = MappedColumn(Float)

    # League position features
    home_league_position: Mapped[int | None] = MappedColumn(Integer)
    away_league_position: Mapped[int | None] = MappedColumn(Integer)
    home_points: Mapped[int | None] = MappedColumn(Integer)
    away_points: Mapped[int | None] = MappedColumn(Integer)
    points_diff: Mapped[int | None] = MappedColumn(Integer)

    # Additional derived features
    home_attack_strength: Mapped[float | None] = MappedColumn(Float)
    away_attack_strength: Mapped[float | None] = MappedColumn(Float)
    home_defense_strength: Mapped[float | None] = MappedColumn(Float)
    away_defense_strength: Mapped[float | None] = MappedColumn(Float)
    home_xg_diff: Mapped[float | None] = MappedColumn(Float)
    away_xg_diff: Mapped[float | None] = MappedColumn(Float)

    # Weather
    temperature: Mapped[float | None] = MappedColumn(Float)
    humidity: Mapped[float | None] = MappedColumn(Float)
    wind_speed: Mapped[float | None] = MappedColumn(Float)
    weather_condition: Mapped[str | None] = MappedColumn(String(100))

    # Referee
    referee_id: Mapped[int | None] = MappedColumn(Integer)
    referee_home_win_rate: Mapped[float | None] = MappedColumn(Float)

    match: Mapped["Match"] = relationship("Match")
