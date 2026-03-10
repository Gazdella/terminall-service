import logging
import aiomysql
from typing import Optional, Dict, Any
from dao.database import get_connection

LOGGER = logging.getLogger(__name__)

class TenantDAO:
    @staticmethod
    async def get_keepz_credentials(tenant_id: str) -> Optional[Dict[str, str]]:
        """Retrieve Keepz credentials for a given tenant."""
        try:
            async with get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("""
                        SELECT keepz_public_key, keepz_private_key, keepz_integrator_id, keepz_receiver_id 
                        FROM tenants 
                        WHERE id = %s
                    """, (tenant_id,))
                    return await cur.fetchone()
        except Exception as e:
            LOGGER.error("Error fetching tenant keepz credentials: %s", e)
            return None
