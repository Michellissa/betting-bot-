"""API route blueprints."""

from betting_bot.api.routes.predictions import router as predictions_router
from betting_bot.api.routes.matches import router as matches_router
from betting_bot.api.routes.stats import router as stats_router
from betting_bot.api.routes.odds import router as odds_router
from betting_bot.api.routes.models import router as models_router
from betting_bot.api.routes.data import router as data_router
from betting_bot.api.routes.health import router as health_router
from betting_bot.api.routes.worldcup import router as worldcup_router

__all__ = [
    "predictions_router",
    "matches_router",
    "stats_router",
    "odds_router",
    "models_router",
    "data_router",
    "health_router",
    "worldcup_router",
]
