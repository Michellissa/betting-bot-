"""World Cup 2026 endpoints."""

from fastapi import APIRouter

from betting_bot.services.worldcup2026_client import WorldCup2026Client

router = APIRouter()


@router.get("/games")
async def wc_games():
    """All 104 World Cup 2026 matches."""
    async with WorldCup2026Client() as c:
        games = await c.get_games()
    return {"games": games, "total": len(games)}


@router.get("/groups")
async def wc_groups():
    """Group standings."""
    async with WorldCup2026Client() as c:
        groups = await c.get_groups()
    return {"groups": groups}


@router.get("/teams")
async def wc_teams():
    """All 48 teams."""
    async with WorldCup2026Client() as c:
        teams = await c.get_teams()
    return {"teams": teams}


@router.get("/stadiums")
async def wc_stadiums():
    """All 16 stadiums."""
    async with WorldCup2026Client() as c:
        stadiums = await c.get_stadiums()
    return {"stadiums": stadiums}


@router.get("/standings")
async def wc_standings():
    """Group standings formatted for frontend."""
    async with WorldCup2026Client() as c:
        groups = await c.get_groups()
    result = []
    for g in groups:
        name = g.get("name")
        teams = g.get("teams", [])
        rows = []
        for t in sorted(teams, key=lambda x: int(x.get("pts", 0)), reverse=True):
            rows.append({
                "team_id": t.get("team_id"),
                "mp": t.get("mp"),
                "w": t.get("w"),
                "d": t.get("d"),
                "l": t.get("l"),
                "pts": t.get("pts"),
                "gf": t.get("gf"),
                "ga": t.get("ga"),
                "gd": t.get("gd"),
            })
        result.append({"group": name, "teams": rows})
    return {"standings": result}
