import logging
import aiomysql
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dao.database import get_connection

LOGGER = logging.getLogger(__name__)

class OrderDAO:
    @staticmethod
    async def create_order(
        order_id: str,
        terminal_id: str,
        keepz_system_id: str,
        amount: float,
        currency: str,
        transaction_id: str,
        pos_url: Optional[str] = None,
        url_for_qr: Optional[str] = None
    ) -> bool:
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        try:
            async with get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        INSERT INTO terminal_orders 
                        (id, terminal_id, keepz_system_id, amount, currency, status, pos_url, url_for_qr, transaction_id, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, 'INITIAL', %s, %s, %s, %s, %s)
                    """, (order_id, terminal_id, keepz_system_id, amount, currency, pos_url, url_for_qr, transaction_id, now, now))
                    return True
        except Exception as e:
            LOGGER.error("Error creating terminal order: %s", e)
            return False

    @staticmethod
    async def update_order_status(
        order_id: str,
        system_id: str,
        keepz_status: str,
        amount: Optional[float] = None
    ) -> bool:
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        try:
            async with get_connection() as conn:
                async with conn.cursor() as cur:
                    if amount is not None:
                        await cur.execute("""
                            UPDATE terminal_orders
                            SET keepz_system_id = %s, keepz_status = %s, status = %s, amount = COALESCE(%s, amount), updated_at = %s
                            WHERE id = %s
                        """, (system_id, keepz_status, keepz_status, amount, now, order_id))
                    else:
                        await cur.execute("""
                            UPDATE terminal_orders
                            SET keepz_system_id = %s, keepz_status = %s, status = %s, updated_at = %s
                            WHERE id = %s
                        """, (system_id, keepz_status, keepz_status, now, order_id))
                    return cur.rowcount > 0
        except Exception as e:
            LOGGER.error("Error updating order status: %s", e)
            return False

    @staticmethod
    async def get_order(order_id: str) -> Optional[Dict[str, Any]]:
        try:
            async with get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute("SELECT * FROM terminal_orders WHERE id = %s", (order_id,))
                    return await cur.fetchone()
        except Exception as e:
            LOGGER.error("Error fetching order: %s", e)
            return None
