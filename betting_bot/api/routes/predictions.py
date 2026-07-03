"""Prediction endpoints."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from betting_bot.api.dependencies.database import get_db
from betting_bot.models.match import Team, League, Match
from betting_bot.models.prediction import Prediction as PredictionModel
from betting_bot.prediction.predictor import PredictionGenerator

router = APIRouter()


class PredictionRequest(BaseModel):
    match_id: int | None = None
    home_team: str | None = None
    away_team: str | None = None


class PredictionResponse(BaseModel):
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    over_2_5_probability: float | None = None
    btts_yes_probability: float | None = None
    home_expected_goals: float | None = None
    away_expected_goals: float | None = None
    confidence_score: float
    risk_score: float
    data_confidence_score: float | None = None


class TeamResponse(BaseModel):
    id: int
    name: str


class LeagueResponse(BaseModel):
    id: int
    name: str


class MatchResponse(BaseModel):
    id: int
    match_date: datetime
    round: int | None = None
    home_team: TeamResponse | None = None
    away_team: TeamResponse | None = None
    league: LeagueResponse | None = None
    is_finished: bool = False


class PredictionListResponse(BaseModel):
    id: int
    match_id: int
    model_name: str
    home_win_probability: float
    draw_probability: float
    away_win_probability: float
    over_2_5_probability: float | None = None
    under_2_5_probability: float | None = None
    btts_yes_probability: float | None = None
    btts_no_probability: float | None = None
    home_expected_goals: float | None = None
    away_expected_goals: float | None = None
    predicted_score: str | None = None
    confidence_score: float
    confidence_level: str | None = None
    risk_score: float
    risk_level: str | None = None
    prediction_date: datetime | None = None
    is_active: bool = True
    model_version: str | None = None
    explanation: str | None = None
    data_confidence_score: float | None = None
    match: MatchResponse | None = None


@router.post("/predict")
async def predict_match(
    request: PredictionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate a prediction for a specific match."""
    if not request.match_id:
        return {"error": "match_id is required"}
    gen = PredictionGenerator(db)
    pred = await gen.predict_match(request.match_id)
    if pred is None:
        return {"error": "Could not generate prediction"}
    return PredictionResponse(
        home_win_probability=pred.home_win_probability or 0.0,
        draw_probability=pred.draw_probability or 0.0,
        away_win_probability=pred.away_win_probability or 0.0,
        over_2_5_probability=pred.over_2_5_probability,
        btts_yes_probability=pred.btts_yes_probability,
        home_expected_goals=pred.home_expected_goals,
        away_expected_goals=pred.away_expected_goals,
        confidence_score=pred.confidence_score or 0.0,
        risk_score=pred.risk_score or 0.0,
        data_confidence_score=pred.data_confidence_score,
    )


@router.get("/upcoming")
async def upcoming_predictions(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get predictions for upcoming matches."""
    stmt = (
        select(PredictionModel)
        .options(
            selectinload(PredictionModel.match)
            .selectinload(Match.home_team),
            selectinload(PredictionModel.match)
            .selectinload(Match.away_team),
            selectinload(PredictionModel.match)
            .selectinload(Match.league),
        )
        .order_by(desc(PredictionModel.prediction_date))
        .limit(limit)
    )
    result = await db.execute(stmt)
    predictions = result.scalars().all()
    def _build_score(home: float | None, away: float | None) -> str | None:
        if home is not None and away is not None:
            return f"{round(home)}-{round(away)}"
        return None

    result_list = []
    for p in predictions:
        match_resp = dict(
            id=p.match.id,
            match_date=str(p.match.match_date),
            round=p.match.round,
            is_finished=p.match.is_finished,
            home_team=dict(id=p.match.home_team.id, name=p.match.home_team.name) if p.match.home_team else None,
            away_team=dict(id=p.match.away_team.id, name=p.match.away_team.name) if p.match.away_team else None,
            league=dict(id=p.match.league.id, name=p.match.league.name) if p.match.league else None,
        ) if p.match else None
        
        item = dict(
            id=p.id,
            match_id=p.match_id,
            model_name=p.model_name,
            home_win_probability=p.home_win_probability or 0.0,
            draw_probability=p.draw_probability or 0.0,
            away_win_probability=p.away_win_probability or 0.0,
            over_2_5_probability=p.over_2_5_probability,
            under_2_5_probability=p.under_2_5_probability,
            btts_yes_probability=p.btts_yes_probability,
            btts_no_probability=p.btts_no_probability,
            home_expected_goals=p.home_expected_goals,
            away_expected_goals=p.away_expected_goals,
            predicted_score=_build_score(p.home_expected_goals, p.away_expected_goals),
            confidence_score=p.confidence_score or 0.0,
            confidence_level=p.confidence_level,
            risk_score=p.risk_score or 0.0,
            risk_level=p.risk_level,
            prediction_date=str(p.prediction_date),
            is_active=p.is_active,
            model_version=p.model_version,
            explanation=p.explanation,
            data_confidence_score=p.data_confidence_score,
            match=match_resp,
        )
        result_list.append(item)
    return result_list


@router.get("/today")
async def today_predictions(
    league: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get predictions for today's matches."""
    return {"predictions": []}


@router.get("/history")
async def prediction_history(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get historical prediction performance."""
    return {"history": [], "accuracy": 0.0, "roi": 0.0}
