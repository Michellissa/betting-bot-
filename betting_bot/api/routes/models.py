"""Model management endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.api.dependencies.database import get_db

router = APIRouter()


@router.get("/")
async def list_models(db: AsyncSession = Depends(get_db)):
    """List all trained models."""
    return {"models": []}


@router.get("/active")
async def active_model(db: AsyncSession = Depends(get_db)):
    """Get the currently active model."""
    return {"model": None}


@router.post("/train")
async def train_models(db: AsyncSession = Depends(get_db)):
    """Trigger model training pipeline."""
    return {"status": "training_started", "message": "Training not yet implemented"}
