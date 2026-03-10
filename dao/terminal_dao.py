import logging
import aiomysql
from typing import Optional, Dict, Any
from dao.database import get_connection

LOGGER = logging.getLogger(__name__)

class TerminalDAO:
    @staticmethod
    async def get_terminal(terminal_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the registered charger/connector mapping for a given terminal ID."""
        try:
            async with get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("""
                        SELECT * FROM terminal_devices 
                        WHERE terminal_id = %s AND status = 'ACTIVE'
                    """, (terminal_id,))
                    return await cur.fetchone()
        except Exception as e:
            LOGGER.error("Error fetching terminal mapping: %s", e)
            return None
