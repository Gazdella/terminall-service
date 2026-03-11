from fastapi import APIRouter, HTTPException, Query
import logging
from pydantic import BaseModel
from typing import Optional
from dao.terminal_dao import TerminalDAO
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/terminals", tags=["Terminal Management"])


class RegisterTerminalRequest(BaseModel):
    terminal_id: str
    charger_id: str
    rfid_number: Optional[str] = None
    device_serial: Optional[str] = None
    tenant_id: Optional[str] = None


class HeartbeatRequest(BaseModel):
    terminal_id: str
    tenant_id: Optional[str] = None


@router.post("/register")
async def register_terminal(req: RegisterTerminalRequest):
    """Register a terminal device linked to a charger in the tenant DB."""
    tenant_id = req.tenant_id or settings.tenant_id
    success = await TerminalDAO.register_terminal(
        terminal_id=req.terminal_id,
        charger_id=req.charger_id,
        rfid_number=req.rfid_number,
        device_serial=req.device_serial,
        tenant_id=tenant_id
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to register terminal")
    
    return {
        "status": "registered",
        "terminal_id": req.terminal_id,
        "charger_id": req.charger_id,
    }


@router.post("/heartbeat")
async def terminal_heartbeat(req: HeartbeatRequest):
    """Receive a heartbeat ping from a terminal device to track online status."""
    tenant_id = req.tenant_id or settings.tenant_id
    success = await TerminalDAO.update_heartbeat(
        terminal_id=req.terminal_id,
        tenant_id=tenant_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Terminal not found or inactive")
    
    return {"status": "ok", "terminal_id": req.terminal_id}


@router.get("")
async def list_terminals(tenant_id: str = Query(default=None)):
    """List all registered terminals with computed online/offline status."""
    resolved_tenant = tenant_id or settings.tenant_id
    terminals = await TerminalDAO.get_all_terminals(tenant_id=resolved_tenant)
    return {"terminals": terminals, "count": len(terminals)}


@router.get("/{terminal_id}")
async def get_terminal(terminal_id: str, tenant_id: str = Query(default=None)):
    """Get terminal device info."""
    resolved_tenant = tenant_id or settings.tenant_id
    terminal = await TerminalDAO.get_terminal(terminal_id, resolved_tenant)
    if not terminal:
        raise HTTPException(status_code=404, detail="Terminal not found")
    return terminal


@router.get("/{terminal_id}/config")
async def get_terminal_config(terminal_id: str, tenant_id: str = Query(default=None)):
    """Return the full runtime config for this terminal.

    The Flutter app calls this on every boot (after self-registering) to pull
    its charger_id, connector list, and payment flow preference from the backend.

    Returns:
        200: { terminal_id, charger_id, prepayment_first, connectors: [{id, type}] }
        404: terminal is unknown / inactive
    """
    resolved_tenant = tenant_id or settings.tenant_id
    config = await TerminalDAO.get_terminal_config(terminal_id, resolved_tenant)
    if config is None:
        raise HTTPException(status_code=404, detail="Terminal not found or inactive")
    return config


