import asyncio
import aiomysql
from config import settings

async def run():
    async with aiomysql.create_pool(host=settings.db_host, port=settings.db_port, user=settings.db_user, password=settings.db_password, db="plugshub", autocommit=True) as pool:
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("DESCRIBE tenants;")
                res = await cur.fetchall()
                for r in res:
                    print(r)

asyncio.run(run())
