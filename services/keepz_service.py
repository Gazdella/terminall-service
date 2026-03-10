import httpx
import logging
from fastapi import HTTPException
from utils.crypto import KeepzCrypto
from config import settings

LOGGER = logging.getLogger(__name__)

class KeepzService:
    async def create_order(self, integrator_order_id: str, amount: float, currency: str, credentials: dict) -> dict:
        crypto = KeepzCrypto(
            public_key_b64=credentials['keepz_public_key'],
            private_key_b64=credentials['keepz_private_key']
        )
        
        payload = {
            "amount": amount,
            "receiverId": credentials['keepz_receiver_id'],
            "receiverType": "BRANCH",
            "integratorId": credentials['keepz_integrator_id'],
            "integratorOrderId": integrator_order_id,
            "softposOrder": True,
        }

        LOGGER.info("Creating Keepz SoftPOS order %s for %.2f %s", integrator_order_id, amount, currency)

        encrypted = crypto.encrypt(payload)
        body = {
            "identifier": credentials['keepz_integrator_id'],
            **encrypted,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    f"{settings.keepz_base_url}/api/integrator/order",
                    json=body,
                    headers={"Content-Type": "application/json"},
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError as e:
                LOGGER.error("Keepz API error: %s - %s", e.response.status_code, e.response.text)
                raise HTTPException(status_code=502, detail=f"Keepz API error: {e.response.status_code}")
            except httpx.RequestError as e:
                LOGGER.error("Keepz network error: %s", e)
                raise HTTPException(status_code=502, detail=f"Network error: {e}")

        resp_data = resp.json()

        if "message" in resp_data:
            LOGGER.error("Keepz error: %s", resp_data["message"])
            raise HTTPException(status_code=400, detail=resp_data["message"])

        decrypted = crypto.decrypt(resp_data["encryptedData"], resp_data["encryptedKeys"])
        LOGGER.info("Order %s created successfully.", integrator_order_id)
        return decrypted

    def process_callback(self, encrypted_data: str, encrypted_keys: str, credentials: dict) -> dict:
        """Decrypts the Keepz callback payload."""
        crypto = KeepzCrypto(
            public_key_b64=credentials['keepz_public_key'],
            private_key_b64=credentials['keepz_private_key']
        )
        return crypto.decrypt(encrypted_data, encrypted_keys)

# Global instance
keepz_service = KeepzService()
