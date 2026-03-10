import logging
import httpx
from config import settings
from dao.terminal_dao import TerminalDAO

LOGGER = logging.getLogger(__name__)

class ChargingBridge:
    @staticmethod
    async def start_charging(terminal_id: str, tenant_id: str, id_tag: str, charger_id: str, connector_id: int, prepaid_amount: float):
        """Trigger a remote start to the OCPP gateway *before* payment (Preauth First)."""
        LOGGER.info("Triggering RemoteStart for Charger %s Connector %s (Tenant %s, Terminal %s)", charger_id, connector_id, tenant_id, terminal_id)
        
        payload = {
            "charger_id": charger_id,
            "connector_id": connector_id,
            "id_tag": id_tag,
            "is_terminal": True,
            "payment_method": "terminal",
            "prepaid_amount": prepaid_amount
        }
        
        headers = {
            "tenant_id": tenant_id
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                 resp = await client.post(
                     f"{settings.ocpp_server_url}/chargers/remote_start",
                     json=payload,
                     headers=headers
                 )
                 resp.raise_for_status()
                 LOGGER.info("Successfully triggered RemoteStart")
                 return True
        except Exception as e:
            LOGGER.error("Failed to trigger RemoteStart: %s", e)
            return False

    @staticmethod
    async def get_active_session_meter(id_tag: str):
        """Poll the session service to check if physical meter values have started."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # We need to query session-service for this specific id_tag to see if it has an active session with meter values
                # Since session-service exposes GET /sessions?id_list=..., we'll need an endpoint to find session by id_tag
                # For now, let's assume we can query by user_tag or we add simple logic here
                resp = await client.get(
                     f"{settings.api_host.replace('8004', '8001')}/api/v1/sessions/active?idTag={id_tag}" # Point to session-service
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data and data.get("sessions"):
                        session = data["sessions"][0]
                        # Return true if the meter has actually started incrementing beyond 0
                        has_meter = session.get("session_energy_used", 0) > 0
                        return {"started": True, "meter_flowing": has_meter, "transaction_id": session.get("id")}
                return {"started": False, "meter_flowing": False, "transaction_id": None}
        except Exception as e:
            LOGGER.error("Failed to check active session: %s", e)
            return {"started": False, "meter_flowing": False, "transaction_id": None}

    @staticmethod
    async def stop_charging(tenant_id: str, id_tag: str, transaction_id: str):
        """Trigger a remote stop to the OCPP gateway if timeout or payment fails."""
        LOGGER.info("Triggering RemoteStop for Transaction %s via keepz fail", transaction_id)
        
        payload = {
            "transaction_id": transaction_id,
            "id_tag": id_tag
        }
        
        headers = {
            "tenant_id": tenant_id
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                 resp = await client.post(
                     f"{settings.ocpp_server_url}/chargers/remote_stop",
                     json=payload,
                     headers=headers
                 )
                 resp.raise_for_status()
                 LOGGER.info("Successfully triggered RemoteStop")
                 return True
        except Exception as e:
            LOGGER.error("Failed to trigger RemoteStop: %s", e)
            return False
            
charging_bridge = ChargingBridge()
