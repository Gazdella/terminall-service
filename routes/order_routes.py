from fastapi import APIRouter, HTTPException
import uuid
import logging
from models.order import CreateOrderRequest, OrderResponse
from services.keepz_service import keepz_service
from dao.order_dao import OrderDAO
from dao.tenant_dao import TenantDAO

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("", response_model=OrderResponse)
async def create_order(req: CreateOrderRequest):
    order_id = str(uuid.uuid4())
    
    try:
        credentials = await TenantDAO.get_keepz_credentials(req.tenant_id)
        if not credentials:
            raise HTTPException(status_code=400, detail="Tenant Keepz credentials not configured")

        # 1. Create Keepz Order
        keepz_resp = await keepz_service.create_order(
            integrator_order_id=order_id,
            amount=req.amount,
            currency=req.currency,
            credentials=credentials
        )
        
        pos_url = keepz_resp.get("posURL")
        url_for_qr = keepz_resp.get("urlForQR")
        system_id = str(keepz_resp.get("systemId", ""))
        
        # 2. Save to DB
        success = await OrderDAO.create_order(
            order_id=order_id,
            terminal_id=req.terminal_id,
            keepz_system_id=system_id,
            amount=req.amount,
            currency=req.currency,
            transaction_id=req.transaction_id,
            pos_url=pos_url,
            url_for_qr=url_for_qr
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save order to database")
            
        order_data = await OrderDAO.get_order(order_id)
        if not order_data:
            raise HTTPException(status_code=500, detail="Order not found after creation")
            
        # Don't serialize datetime directly, let pydantic model handle it
        return order_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create order: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str):
    order = await OrderDAO.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
