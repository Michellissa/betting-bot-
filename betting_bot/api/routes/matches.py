"""Match data endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from betting_bot.api.dependencies.database import get_db
from betting_bot.models.match import Match

router = APIRouter()


@router.get("/")
async def list_matches(
    league_id: int | None = Query(None, description="Filter by league ID"),
    season_id: int | None = Query(None, description="Filter by season ID"),
    finished: bool | None = Query(None, description="Filter by finished status"),
    status: str | None = Query(None, description="Match status (upcoming/finished)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List matches with optional filtering."""
    base = select(Match)

    if finished is not None:
        base = base.where(Match.is_finished == finished)
    elif status == "finished":
        base = base.where(Match.is_finished == True)
    elif status == "upcoming":
        base = base.where(Match.is_finished == False)

    if league_id is not None:
        base = base.where(Match.league_id == league_id)

    if season_id is not None:
        base = base.where(Match.season_id == season_id)

    count_q = select(func.count()).select_from(base.subquery())
    total = await db.scalar(count_q) or 0

    stmt = (
        base.options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.league),
            selectinload(Match.season),
        )
        .order_by(desc(Match.match_date))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    matches = result.scalars().all()
    return {"matches": matches, "total": total, "limit": limit, "offset": offset}


@router.get("/live")
async def live_matches(
    limit: int = Query(20, ge=1, le=100),
):
    """Fetch live football matches from SportScore.

    Disables file-based caching so live scores are always fresh.
    """
    from betting_bot.services.sportscore_client import SportScoreClient

    client = SportScoreClient()
    try:
        data = await client.get_matches(sport="football", limit=limit, use_cache=False)
        matches = data.get("matches", [])
        parsed = [client.parse_match_summary(m) for m in matches]
        return {"matches": parsed, "source": "sportscore", "total": len(parsed)}
    except Exception as e:
        return {"matches": [], "source": "sportscore", "error": str(e), "total": 0}
    finally:
        await client.close()


@router.get("/live/{slug}")
async def live_match_detail(slug: str):
    """Fetch live match detail (with incidents/goals) from SportScore by slug.

    The slug is the URL path segment from SportScore, e.g.
    ``portugal-vs-croatia-jul-2-2026``.
    """
    from betting_bot.services.sportscore_client import SportScoreClient

    client = SportScoreClient()
    try:
        data = await client.get_match_detail(slug=slug, sport="football")
        parsed = client.parse_match_detail(data)
        return {"match": parsed, "source": "sportscore", "updated": data.get("updated", "")}
    except Exception as e:
        return {"match": None, "source": "sportscore", "error": str(e)}
    finally:
        await client.close()


@router.get("/{match_id}")
async def get_match(match_id: int, db: AsyncSession = Depends(get_db)):
    """Get detailed information about a specific match."""
    stmt = (
        select(Match)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.league),
            selectinload(Match.season),
        )
        .where(Match.id == match_id)
    )
    result = await db.execute(stmt)
    match = result.scalar_one_or_none()
    if match is None:
        return {"error": "Match not found"}
    return match
