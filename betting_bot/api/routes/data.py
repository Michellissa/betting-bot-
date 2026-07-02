"""Data ingestion endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.api.dependencies.database import get_db

router = APIRouter()


@router.post("/fetch/matches")
async def fetch_matches(
    league: str | None = None,
    season: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Fetch match data from external APIs."""
    return {"status": "fetch_started", "message": "Data fetching not yet implemented"}


@router.post("/fetch/odds")
async def fetch_odds(
    match_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Fetch odds data from external APIs."""
    return {"status": "fetch_started", "message": "Data fetching not yet implemented"}


@router.get("/sources")
async def list_sources():
    """List configured data sources."""
    return {
        "sources": [
            {"name": "football-data.org", "enabled": True},
            {"name": "api-football", "enabled": True},
            {"name": "the-odds-api", "enabled": True},
        ]
    }
