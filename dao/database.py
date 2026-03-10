import aiomysql
import logging
from contextlib import asynccontextmanager
from config import settings

LOGGER = logging.getLogger(__name__)

pool = None

async def init_db_pool():
    global pool
    if pool is not None:
        return
        
    LOGGER.info("Connecting to MySQL at %s:%s/%s", settings.db_host, settings.db_port, settings.db_name)
    try:
        pool = await aiomysql.create_pool(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            db=settings.db_name,
            autocommit=True,
            minsize=2,
            maxsize=10,
        )
        
        # Create tables if not exists
        async with pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS terminal_orders (
                        id VARCHAR(255) PRIMARY KEY,
                        terminal_id VARCHAR(255) NOT NULL,
                        keepz_system_id VARCHAR(255),
                        amount DECIMAL(10,2) NOT NULL,
                        currency VARCHAR(10) NOT NULL DEFAULT 'GEL',
                        status VARCHAR(50) NOT NULL DEFAULT 'INITIAL',
                        pos_url TEXT,
                        url_for_qr TEXT,
                        error_code VARCHAR(255),
                        error_message TEXT,
                        keepz_status VARCHAR(50),
                        transaction_id VARCHAR(255),
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        INDEX idx_terminal (terminal_id),
                        INDEX idx_status (status)
                    )
                """)
                
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS terminal_devices (
                        terminal_id VARCHAR(255) PRIMARY KEY,
                        charger_id VARCHAR(255) NOT NULL,
                        connector_id INT NOT NULL,
                        location_id VARCHAR(255),
                        status VARCHAR(50) DEFAULT 'ACTIVE',
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        INDEX idx_charger (charger_id)
                    )
                """)
        LOGGER.info("Database pool initialized and tables ensured.")
    except Exception as e:
        LOGGER.error("Failed to initialize database pool: %s", e)
        raise

async def close_db_pool():
    global pool
    if pool is not None:
        pool.close()
        await pool.wait_closed()
        pool = None
        LOGGER.info("Database pool closed.")

@asynccontextmanager
async def get_connection():
    global pool
    if pool is None:
        await init_db_pool()
    async with pool.acquire() as conn:
        yield conn
