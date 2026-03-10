from pydantic import BaseModel, Field
from typing import Optional

class TerminalSessionStartRequest(BaseModel):
    terminal_id: str = Field(..., description="Unique terminal ID (SN)")
    tenant_id: Optional[str] = Field(None, description="Tenant ID (optional, uses server default)")
    id_tag: str = Field(..., description="RFID card tag assigned to this terminal")
    charger_id: str = Field(..., description="OCPP Charger ID")
    connector_id: int = Field(..., description="Target connector ID")
    prepaid_amount: float = Field(..., description="Requested charging amount in GEL")
    gateway: str = Field("keepz", description="The gateway to process through")

class TerminalSessionStopRequest(BaseModel):
    terminal_id: str = Field(..., description="Unique terminal ID (SN)")
    tenant_id: Optional[str] = Field(None, description="Tenant ID (optional, uses server default)")
    id_tag: str = Field(..., description="RFID card tag assigned to this terminal")
    transaction_id: str = Field(..., description="OCPP Transaction ID")
