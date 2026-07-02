"""Odds analysis endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.api.dependencies.database import get_db

router = APIRouter()


@router.get("/")
async def list_odds(
    match_id: int | None = Query(None),
    bookmaker: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List odds with optional filtering."""
    return {"odds": []}


@router.get("/value-bets")
async def value_bets(
    min_ev: float = Query(0.05, description="Minimum expected value"),
    league: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Find value bets across available matches."""
    return {"value_bets": []}


@router.get("/arbitrage")
async def arbitrage_opportunities(
    db: AsyncSession = Depends(get_db),
):
    """Find arbitrage opportunities across bookmakers."""
    return {"arbitrage": []}
