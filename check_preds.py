import sys; sys.path.insert(0, '.')
import asyncio
from sqlalchemy import text
from betting_bot.database.session import get_async_session, init_db

async def main():
    await init_db()
    async for session in get_async_session():
        r = await session.execute(text('SELECT id, home_expected_goals, away_expected_goals, predicted_score, explanation FROM predictions LIMIT 3'))
        for row in r:
            print(dict(row._mapping))

asyncio.run(main())
