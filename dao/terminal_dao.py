import logging
import aiomysql
from typing import Optional, Dict, Any
from dao.database import get_connection
from config import settings

LOGGER = logging.getLogger(__name__)

class TerminalDAO:
    @staticmethod
    async def get_terminal(terminal_id: str, tenant_id: str = None) -> Optional[Dict[str, Any]]:
        """Retrieve the registered terminal device with its rfid_number from tenant DB."""
        resolved_tenant = tenant_id or settings.tenant_id
        try:
            async with get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(f"""
                        SELECT * FROM `tenant{resolved_tenant}`.`terminal_devices`
                        WHERE terminal_id = %s AND UPPER(status) = 'ACTIVE'
                    """, (terminal_id,))
                    return await cur.fetchone()
        except Exception as e:
            LOGGER.error("Error fetching terminal mapping: %s", e)
            return None

    @staticmethod
    async def register_terminal(
        terminal_id: str,
        charger_id: str,
        rfid_number: str = None,
        device_serial: str = None,
        tenant_id: str = None
    ) -> bool:
        """Register a new terminal device in tenant DB."""
        resolved_tenant = tenant_id or settings.tenant_id
        try:
            async with get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(f"""
                        INSERT INTO `tenant{resolved_tenant}`.`terminal_devices`
                        (terminal_id, rfid_number, charger_id, device_serial, status, last_seen_at, is_online, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, 'ACTIVE', NOW(), TRUE, NOW(), NOW())
                        ON DUPLICATE KEY UPDATE
                            rfid_number = VALUES(rfid_number),
                            charger_id = VALUES(charger_id),
                            device_serial = VALUES(device_serial),
                            status = 'ACTIVE',
                            last_seen_at = NOW(),
                            is_online = TRUE,
                            updated_at = NOW()
                    """, (terminal_id, rfid_number, charger_id, device_serial))
                    return True
        except Exception as e:
            LOGGER.error("Error registering terminal: %s", e)
            return False

    @staticmethod
    async def update_heartbeat(terminal_id: str, tenant_id: str = None) -> bool:
        """Update last_seen_at timestamp for a terminal device."""
        resolved_tenant = tenant_id or settings.tenant_id
        try:
            async with get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(f"""
                        UPDATE `tenant{resolved_tenant}`.`terminal_devices`
                        SET last_seen_at = NOW(), is_online = TRUE, updated_at = NOW()
                        WHERE terminal_id = %s AND UPPER(status) = 'ACTIVE'
                    """, (terminal_id,))
                    return cur.rowcount > 0
        except Exception as e:
            LOGGER.error("Error updating heartbeat for terminal %s: %s", terminal_id, e)
            return False

    @staticmethod
    async def get_all_terminals(tenant_id: str = None) -> list:
        """Retrieve all terminal devices with computed online/offline status."""
        resolved_tenant = tenant_id or settings.tenant_id
        try:
            async with get_connection() as conn:
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(f"""
                        SELECT *,
                            CASE
                                WHEN last_seen_at IS NOT NULL
                                     AND last_seen_at > NOW() - INTERVAL 2 MINUTE
                                THEN TRUE
                                ELSE FALSE
                            END AS computed_online
                        FROM `tenant{resolved_tenant}`.`terminal_devices`
                        WHERE UPPER(status) = 'ACTIVE'
                        ORDER BY terminal_id
                    """)
                    return await cur.fetchall()
        except Exception as e:
            LOGGER.error("Error fetching all terminals: %s", e)
            return []

    @staticmethod
    async def set_offline(terminal_id: str, tenant_id: str = None) -> bool:
        """Mark a terminal as offline in DB."""
        resolved_tenant = tenant_id or settings.tenant_id
        try:
            async with get_connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(f"""
                        UPDATE `tenant{resolved_tenant}`.`terminal_devices`
                        SET is_online = FALSE, updated_at = NOW()
                        WHERE terminal_id = %s
                    """, (terminal_id,))
                    return cur.rowcount > 0
        except Exception as e:
            LOGGER.error("Error marking terminal %s offline: %s", terminal_id, e)
            return False

    @staticmethod
    async def get_terminal_config(terminal_id: str, tenant_id: str = None) -> Optional[Dict[str, Any]]:
        """Return full config for a terminal: charger_id (OCPP), connectors, prepaymentFirst.

        Joins terminal_devices → chargers → connectors so the app can self-configure on boot.
        Returns None if the terminal is unknown or charger is not yet assigned.
        """
        resolved_tenant = tenant_id or settings.tenant_id
        try:
            async with get_connection() as conn:
                # 1. Get terminal row + resolve to OCPP charger_id
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(f"""
                        SELECT
                            td.terminal_id,
                            td.charger_id   AS charger_db_id,
                            td.rfid_number,
                            ch.charger_id   AS ocpp_charger_id,
                            COALESCE(ch.prepayment_first, FALSE) AS prepayment_first
                        FROM `tenant{resolved_tenant}`.terminal_devices td
                        LEFT JOIN `tenant{resolved_tenant}`.chargers ch
                               ON ch.id = td.charger_id
                        WHERE td.terminal_id = %s
                          AND UPPER(td.status) = 'ACTIVE'
                    """, (terminal_id,))
                    terminal = await cur.fetchone()

                if not terminal:
                    LOGGER.warning("[Config] Terminal %s not found", terminal_id)
                    return None

                ocpp_charger_id = terminal.get("ocpp_charger_id")
                if not ocpp_charger_id:
                    LOGGER.warning("[Config] Terminal %s has no charger assigned yet", terminal_id)
                    # Return partial config so the app knows it's registered but unassigned
                    return {
                        "terminal_id": terminal_id,
                        "charger_id": "",
                        "prepayment_first": False,
                        "connectors": [],
                    }

                # 2. Fetch connectors for this charger
                async with conn.cursor(aiomysql.DictCursor) as cur:
                    await cur.execute(f"""
                        SELECT
                            c.connector_id               AS id,
                            COALESCE(c.standard, 'Type2') AS type
                        FROM `tenant{resolved_tenant}`.connectors c
                        WHERE c.charger_id = %s
                        ORDER BY c.connector_id
                    """, (ocpp_charger_id,))
                    connectors = await cur.fetchall()

                return {
                    "terminal_id": terminal_id,
                    "charger_id": ocpp_charger_id,
                    "prepayment_first": bool(terminal.get("prepayment_first", False)),
                    "connectors": [
                        {"id": int(c["id"]), "type": c["type"]}
                        for c in connectors
                    ],
                }
        except Exception as e:
            LOGGER.error("[Config] Error fetching config for terminal %s: %s", terminal_id, e)
            return None
