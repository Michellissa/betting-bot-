"""Test if PredictionListResponse serializes correctly through FastAPI's JSONResponse."""

import sys; sys.path.insert(0, '.')
import json
from datetime import datetime
from fastapi.responses import JSONResponse
from betting_bot.api.routes.predictions import PredictionListResponse, MatchResponse, TeamResponse, LeagueResponse

p = PredictionListResponse(
    id=1,
    match_id=100,
    model_name='test',
    home_win_probability=0.5,
    draw_probability=0.3,
    away_win_probability=0.2,
    over_2_5_probability=0.6,
    under_2_5_probability=0.4,
    btts_yes_probability=0.5,
    btts_no_probability=0.5,
    home_expected_goals=1.5,
    away_expected_goals=0.8,
    predicted_score='2-1',
    confidence_score=0.2,
    confidence_level='low',
    risk_score=0.8,
    risk_level='high',
    prediction_date=datetime.now(),
    is_active=True,
    model_version='v1',
    explanation='Test explanation',
    match=MatchResponse(
        id=100,
        match_date=datetime(2026, 7, 6, 17, 0, 0),
        round=5,
        home_team=TeamResponse(id=1, name='Team A'),
        away_team=TeamResponse(id=2, name='Team B'),
        league=LeagueResponse(id=1, name='Test League'),
        is_finished=False,
    ),
)

# Test 1: Direct model_dump
print("=== model_dump() ===")
d = p.model_dump()
print('Keys:', sorted(d.keys()))
print('home_expected_goals:', d.get('home_expected_goals'))
print('away_expected_goals:', d.get('away_expected_goals'))
print('predicted_score:', d.get('predicted_score'))
print('explanation:', d.get('explanation'))

# Test 2: Through JSONResponse
print("\n=== JSONResponse ===")
resp = JSONResponse(content=[p.model_dump(mode='json')])
body = resp.body.decode()
data = json.loads(body)
print('Keys:', sorted(data[0].keys()))
print('home_expected_goals:', data[0].get('home_expected_goals'))
print('away_expected_goals:', data[0].get('away_expected_goals'))
print('predicted_score:', data[0].get('predicted_score'))
print('explanation:', data[0].get('explanation'))

# Test 3: The model itself as JSONResponse content
print("\n=== JSONResponse(content=[model]) ===")
resp2 = JSONResponse(content=[p])
body2 = resp2.body.decode()
data2 = json.loads(body2)
print('Keys:', sorted(data2[0].keys()))
print('home_expected_goals:', data2[0].get('home_expected_goals'))
print('away_expected_goals:', data2[0].get('away_expected_goals'))
print('predicted_score:', data2[0].get('predicted_score'))
print('explanation:', data2[0].get('explanation'))

# Test 4: Via FastAPI's jsonable_encoder
print("\n=== jsonable_encoder ===")
from fastapi.encoders import jsonable_encoder
encoded = jsonable_encoder([p])
print('Keys:', sorted(encoded[0].keys()))
print('home_expected_goals:', encoded[0].get('home_expected_goals'))
print('away_expected_goals:', encoded[0].get('away_expected_goals'))
print('predicted_score:', encoded[0].get('predicted_score'))
print('explanation:', encoded[0].get('explanation'))
