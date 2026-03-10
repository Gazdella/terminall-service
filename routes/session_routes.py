from fastapi import APIRouter, HTTPException, Query
import logging
from models.session import TerminalSessionStartRequest, TerminalSessionStopRequest
from services.charging_bridge import charging_bridge
from dao.terminal_dao import TerminalDAO
from dao.database import get_connection
from config import settings
import aiomysql

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/session", tags=["Session"])

@router.post("/start")
async def start_session(req: TerminalSessionStartRequest):
    """Trigger a RemoteStartTransaction on the OCPP server."""
    tenant_id = req.tenant_id or settings.tenant_id
    success = await charging_bridge.start_charging(
        terminal_id=req.terminal_id, 
        tenant_id=tenant_id,
        id_tag=req.id_tag,
        charger_id=req.charger_id,
        connector_id=req.connector_id,
        prepaid_amount=req.prepaid_amount
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to initialize charging session")
        
    return {
        "status": "STARTED",
        "terminal_id": req.terminal_id,
        "message": "Sent RemoteStartTransaction to charger. Please wait for meter values."
    }

@router.post("/stop")
async def stop_session(req: TerminalSessionStopRequest):
    """Trigger a RemoteStopTransaction on the OCPP server for aborted sessions/failures."""
    tenant_id = req.tenant_id or settings.tenant_id
    success = await charging_bridge.stop_charging(
        tenant_id=tenant_id,
        id_tag=req.id_tag,
        transaction_id=req.transaction_id
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to initialize remote stop")

    return {
        "status": "STOPPED",
        "terminal_id": req.terminal_id,
        "transaction_id": req.transaction_id
    }

@router.get("/{id_tag}/meter")
async def get_session_meter(id_tag: str):
    """Poll endpoint for the Flutter App to check if charging started (meter > 0)"""
    status = await charging_bridge.get_active_session_meter(id_tag)
    return status

@router.get("/charger/{charger_id}/connector/{connector_id}/status")
async def get_connector_status(
    charger_id: str,
    connector_id: int,
    tenant_id: str = Query(default=None)
):
    """Direct DB poll to check if the charger and connector are available to charge via terminal"""
    resolved_tenant_id = tenant_id or settings.tenant_id
    try:
        async with get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # We expect the client to append ?tenant_id= UUID parameter
                await cur.execute(f"""
                    SELECT status, error_code 
                    FROM `tenant{resolved_tenant_id}`.connectors 
                    WHERE charger_id = %s AND connector_id = %s
                """, (charger_id, connector_id))
                res = await cur.fetchone()
                if res is None:
                     raise HTTPException(status_code=404, detail="Connector not found")
                return res
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to query connector status: %s", e)
        raise HTTPException(status_code=500, detail="Error fetching status")
