"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from betting_bot.core.config import get_settings
from betting_bot.api.routes import predictions_router, matches_router, stats_router, odds_router, models_router, data_router, health_router, worldcup_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    settings = get_settings()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    yield
    logger.info("Shutting down application")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Professional football betting analysis platform",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, prefix="/api/v1", tags=["Health"])
    app.include_router(matches_router, prefix="/api/v1/matches", tags=["Matches"])
    app.include_router(stats_router, prefix="/api/v1", tags=["Stats"])
    app.include_router(predictions_router, prefix="/api/v1/predictions", tags=["Predictions"])
    app.include_router(odds_router, prefix="/api/v1/odds", tags=["Odds"])
    app.include_router(models_router, prefix="/api/v1/models", tags=["Models"])
    app.include_router(data_router, prefix="/api/v1/data", tags=["Data"])
    app.include_router(worldcup_router, prefix="/api/v1/worldcup", tags=["World Cup 2026"])

    return app
