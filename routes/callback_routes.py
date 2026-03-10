import asyncio
from fastapi import APIRouter, HTTPException
import logging
from models.order import KeepzCallbackBody
from services.keepz_service import keepz_service
from dao.order_dao import OrderDAO
from dao.tenant_dao import TenantDAO
from services.charging_bridge import charging_bridge

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Callbacks"])

@router.post("/callback/{tenant_id}")
async def keepz_callback(tenant_id: str, body: KeepzCallbackBody):
    try:
        credentials = await TenantDAO.get_keepz_credentials(tenant_id)
        if not credentials:
            raise HTTPException(status_code=400, detail="Tenant Keepz credentials not found")

        decrypted = keepz_service.process_callback(
            encrypted_data=body.encryptedData,
            encrypted_keys=body.encryptedKeys,
            credentials=credentials
        )
        
        logger.info("Keepz callback received: %s", decrypted)
        
        order_id = decrypted.get("integratorOrderId")
        system_id = str(decrypted.get("systemId", ""))
        keepz_status = decrypted.get("status", "UNKNOWN")
        amount = decrypted.get("amount")
        
        if not order_id:
            raise HTTPException(status_code=400, detail="Missing integratorOrderId")
            
        # Update order
        await OrderDAO.update_order_status(
            order_id=order_id,
            system_id=system_id,
            keepz_status=keepz_status,
            amount=amount
        )

        # Retrieve order to get related terminal info for rabbitmq and ocpi
        order = await OrderDAO.get_order(order_id)
        
        if order:
            from services.rabbitmq_publisher import rmq_publisher
            await rmq_publisher.publish_terminal_transaction(
                tenant_id=tenant_id,
                terminal_id=order["terminal_id"],
                order_id=order_id,
                keepz_status=keepz_status,
                amount=amount or order.get("amount", 0.0),
                currency=order.get("currency", "GEL")
            )
        
        # In Preauth-First, charging has already started before this callback.
        # If the payment fails (e.g., card declined, user cancelled out of the wallet), we must STOP charging.
        if keepz_status != "COMPLETED":
            if order:
                asyncio.create_task(
                    charging_bridge.stop_charging(
                        tenant_id=tenant_id,
                        id_tag=f"TERMINAL_{order['terminal_id']}",
                        transaction_id=order_id # Order id fallback
                    )
                )
                
        return {"status": "received", "orderId": order_id, "keepzStatus": keepz_status}
        
    except Exception as e:
        logger.error("Callback processing failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
