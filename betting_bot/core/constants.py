"""Project-wide constants and enumerations."""

from enum import Enum


class League(str, Enum):
    """Supported football leagues."""

    PREMIER_LEAGUE = "PL"
    LA_LIGA = "PD"
    SERIE_A = "SA"
    BUNDESLIGA = "BL1"
    LIGUE_1 = "FL1"
    CHAMPIONS_LEAGUE = "CL"
    EUROPA_LEAGUE = "EL"
    EREDIVISIE = "DED"
    PRIMEIRA_LIGA = "PPL"
    CHAMPIONSHIP = "ELC"
    ALLSVENSKAN = "ALL"
    LIGA_PORTUGAL = "LP"
    MLS = "MLS"
    BRAZIL_SERIE_A = "BSA"
    ARGENTINA_PRIMERA = "ARP"

    @property
    def display_name(self) -> str:
        names = {
            "PL": "Premier League",
            "PD": "La Liga",
            "SA": "Serie A",
            "BL1": "Bundesliga",
            "FL1": "Ligue 1",
            "CL": "Champions League",
            "EL": "Europa League",
            "DED": "Eredivisie",
            "PPL": "Primeira Liga",
            "ELC": "Championship",
            "ALL": "Allsvenskan",
            "LP": "Liga Portugal",
            "MLS": "MLS",
            "BSA": "Brasileirão Série A",
            "ARP": "Argentina Primera",
        }
        return names.get(self.value, self.value)


class PredictionType(str, Enum):
    """Types of predictions the system can make."""

    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"
    OVER_2_5 = "over_2_5"
    UNDER_2_5 = "under_2_5"
    BTTS_YES = "btts_yes"
    BTTS_NO = "btts_no"


class ModelName(str, Enum):
    """Available ML models."""

    RANDOM_FOREST = "random_forest"
    XGBOOST = "xgboost"
    LIGHTGBM = "lightgbm"
    CATBOOST = "catboost"
    LOGISTIC_REGRESSION = "logistic_regression"


class MatchResult(str, Enum):
    """Possible match outcomes."""

    HOME_WIN = "H"
    DRAW = "D"
    AWAY_WIN = "A"

    @classmethod
    def from_score(cls, home_goals: int, away_goals: int) -> "MatchResult":
        if home_goals > away_goals:
            return cls.HOME_WIN
        elif home_goals < away_goals:
            return cls.AWAY_WIN
        return cls.DRAW


class DataSource(str, Enum):
    """Supported data sources."""

    FOOTBALL_DATA_ORG = "football_data_org"
    API_FOOTBALL = "api_football"
    ODDS_API = "odds_api"
    UNDERSTAT = "understat"
    STATSBOMB = "statsbomb"
    FBREF = "fbref"
    THESTATSAPI = "thestatsapi"
    SPORTMONKS = "sportmonks"
    SPORTRADAR = "sportradar"
    SOCCERWAY = "soccerway"
    FLASHSCORE = "flashscore"


class ConfidenceLevel(str, Enum):
    """Confidence levels for predictions."""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        if score >= 0.85:
            return cls.VERY_HIGH
        elif score >= 0.70:
            return cls.HIGH
        elif score >= 0.55:
            return cls.MEDIUM
        elif score >= 0.40:
            return cls.LOW
        return cls.VERY_LOW


class RiskLevel(str, Enum):
    """Risk levels for betting suggestions."""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

    @classmethod
    def from_value(cls, value: float) -> "RiskLevel":
        if value <= 0.05:
            return cls.VERY_LOW
        elif value <= 0.15:
            return cls.LOW
        elif value <= 0.30:
            return cls.MEDIUM
        elif value <= 0.50:
            return cls.HIGH
        return cls.VERY_HIGH


class FeatureCategory(str, Enum):
    """Categories for feature organization."""

    FORM = "form"
    GOALS = "goals"
    XG = "xg"
    ELOC = "elo"
    POSSESSION = "possession"
    SHOTS = "shots"
    DEFENSE = "defense"
    DISCIPLINE = "discipline"
    REST = "rest"
    TRAVEL = "travel"
    H2H = "head_to_head"
    HOME_AWAY = "home_away"
    MANAGER = "manager"
    INJURY = "injury"
    WEATHER = "weather"
    REFEREE = "referee"
    DERIVED = "derived"


# Data source metadata
DATA_SOURCE_INFO: dict[DataSource, dict] = {
    DataSource.FOOTBALL_DATA_ORG: {
        "name": "Football-Data.org",
        "url": "https://www.football-data.org",
        "base_url": "https://api.football-data.org/v4",
        "free_tier": True,
        "rate_limit_per_min": 10,
        "rate_limit_per_day": None,
        "features": ["matches", "standings", "teams", "scorers"],
        "leagues": 12,
        "history_years": None,
        "odds": False,
        "xg": False,
    },
    DataSource.API_FOOTBALL: {
        "name": "API-Football",
        "url": "https://www.api-football.com",
        "base_url": "https://v3.football.api-sports.io",
        "free_tier": True,
        "rate_limit_per_min": None,
        "rate_limit_per_day": 100,
        "features": [
            "matches", "standings", "teams", "players",
            "statistics", "lineups", "injuries", "predictions",
        ],
        "leagues": 200,
        "history_years": 10,
        "odds": False,
        "xg": False,
    },
    DataSource.ODDS_API: {
        "name": "The Odds API",
        "url": "https://the-odds-api.com",
        "base_url": "https://api.the-odds-api.com/v4",
        "free_tier": True,
        "rate_limit_per_min": None,
        "rate_limit_per_day": 500,
        "features": ["odds", "scores"],
        "leagues": 150,
        "history_years": None,
        "odds": True,
        "xg": False,
    },
    DataSource.UNDERSTAT: {
        "name": "Understat",
        "url": "https://understat.com",
        "base_url": None,
        "free_tier": True,
        "rate_limit_per_min": None,
        "rate_limit_per_day": None,
        "features": ["xg", "matches", "player_stats"],
        "leagues": 6,
        "history_years": 7,
        "odds": False,
        "xg": True,
        "requires_scraping": True,
    },
    DataSource.STATSBOMB: {
        "name": "StatsBomb Open Data",
        "url": "https://github.com/statsbomb/open-data",
        "base_url": "https://raw.githubusercontent.com/statsbomb/open-data/master/data",
        "free_tier": True,
        "rate_limit_per_min": None,
        "rate_limit_per_day": None,
        "features": ["events", "matches", "lineups", "xg"],
        "leagues": 20,
        "history_years": 8,
        "odds": False,
        "xg": True,
        "note": "Open dataset, no API key needed. Data via GitHub raw files.",
    },
    DataSource.FBREF: {
        "name": "FBref",
        "url": "https://fbref.com",
        "base_url": "https://fbref.com/en",
        "free_tier": True,
        "rate_limit_per_min": None,
        "rate_limit_per_day": None,
        "features": ["matches", "player_stats", "team_stats", "xg", "scouting"],
        "leagues": 15,
        "history_years": 10,
        "odds": False,
        "xg": True,
        "requires_scraping": True,
        "note": "Requires scraping, robots.txt allows limited access.",
    },
    DataSource.THESTATSAPI: {
        "name": "TheStatsAPI",
        "url": "https://thestatsapi.com",
        "base_url": "https://api.thestatsapi.com/v1",
        "free_tier": False,
        "rate_limit_per_min": None,
        "rate_limit_per_day": None,
        "features": [
            "matches", "standings", "teams", "players",
            "odds", "xg", "statistics", "history",
        ],
        "leagues": 150,
        "history_years": 10,
        "odds": True,
        "xg": True,
        "trial_days": 7,
        "pricing": "From $50/month",
    },
    DataSource.SPORTMONKS: {
        "name": "Sportmonks",
        "url": "https://www.sportmonks.com",
        "base_url": "https://api.sportmonks.com/v3",
        "free_tier": False,
        "rate_limit_per_min": None,
        "rate_limit_per_day": None,
        "features": [
            "matches", "standings", "teams", "players",
            "odds", "xg", "statistics", "predictions",
        ],
        "leagues": 2200,
        "history_years": None,
        "odds": True,
        "xg": True,
        "note": "Modular add-on pricing (leagues, odds, xG sold separately).",
    },
    DataSource.SPORTRADAR: {
        "name": "Sportradar",
        "url": "https://developer.sportradar.com",
        "base_url": None,
        "free_tier": False,
        "rate_limit_per_min": None,
        "rate_limit_per_day": None,
        "features": ["matches", "standings", "teams", "odds", "statistics", "live"],
        "leagues": 1000,
        "history_years": None,
        "odds": True,
        "xg": True,
        "note": "Enterprise licensing, requires sales contact.",
    },
    DataSource.SOCCERWAY: {
        "name": "Soccerway",
        "url": "https://www.soccerway.com",
        "base_url": None,
        "free_tier": True,
        "rate_limit_per_min": None,
        "rate_limit_per_day": None,
        "features": ["matches", "standings", "teams", "statistics"],
        "leagues": 200,
        "history_years": None,
        "odds": False,
        "xg": False,
        "requires_scraping": True,
    },
    DataSource.FLASHSCORE: {
        "name": "Flashscore",
        "url": "https://www.flashscore.com",
        "base_url": None,
        "free_tier": True,
        "rate_limit_per_min": None,
        "rate_limit_per_day": None,
        "features": ["matches", "standings", "statistics", "odds"],
        "leagues": 1000,
        "history_years": None,
        "odds": True,
        "xg": False,
        "requires_scraping": True,
    },
}

# Feature store keys
FEATURE_STORE_TABLE = "feature_store"
MODEL_REGISTRY_TABLE = "model_registry"
PREDICTION_CACHE_TTL = 1800  # 30 minutes

# Default training parameters
DEFAULT_TEST_SPLIT = 0.20
DEFAULT_VALIDATION_SPLIT = 0.10
DEFAULT_CV_FOLDS = 5
DEFAULT_RANDOM_STATE = 42
DEFAULT_N_TRIALS_OPTUNA = 100

# Betting constants
KELLY_FRACTION_DEFAULT = 0.25
MIN_POSITIVE_EV = 0.05
MAX_STAKE_PERCENTAGE = 0.05  # 5% of bankroll
