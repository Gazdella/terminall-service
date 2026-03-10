import asyncio
from dao.database import get_connection
import aiomysql

async def run():
    async with get_connection() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("DESCRIBE tenants;")
            res = await cur.fetchall()
            for r in res:
                print(r['Field'])

asyncio.run(run())
