"""Dashboard statistics endpoint."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.api.dependencies.database import get_db
from betting_bot.models.match import Match
from betting_bot.models.prediction import Prediction
from betting_bot.models.model_registry import ModelRegistry

router = APIRouter()


class DashboardStats(BaseModel):
    total_matches: int
    finished_matches: int
    upcoming_matches: int
    total_predictions: int
    active_models: int


@router.get("/stats", response_model=DashboardStats)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get dashboard statistics."""
    total = await db.scalar(select(func.count(Match.id)))
    finished = await db.scalar(select(func.count(Match.id)).where(Match.is_finished == True))
    upcoming = await db.scalar(select(func.count(Match.id)).where(Match.is_finished == False))
    predictions = await db.scalar(select(func.count(Prediction.id)))
    active = await db.scalar(select(func.count(ModelRegistry.id)).where(ModelRegistry.is_active == True))

    return DashboardStats(
        total_matches=total or 0,
        finished_matches=finished or 0,
        upcoming_matches=upcoming or 0,
        total_predictions=predictions or 0,
        active_models=active or 0,
    )
