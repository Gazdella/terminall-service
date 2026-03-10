from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class CreateOrderRequest(BaseModel):
    """Request from Z80 terminal to create a payment order."""
    amount: float = Field(..., gt=0, description="Payment amount in GEL")
    currency: str = Field(default="GEL", description="ISO 4217 currency code")
    terminal_id: str = Field(..., description="Unique terminal identifier (e.g. SN or UUID)")
    transaction_id: str = Field(..., description="OCPP Session ID starting before Payment")
    tenant_id: str = Field(..., description="Tenant ID to fetch credentials")

class OrderResponse(BaseModel):
    id: str
    terminal_id: str
    transaction_id: str
    amount: float
    currency: str
    status: str
    pos_url: Optional[str] = None
    url_for_qr: Optional[str] = None
    created_at: datetime
    
class KeepzCallbackBody(BaseModel):
    """The raw body from Keepz POST."""
    encryptedData: str
    encryptedKeys: str
    aes: Optional[bool] = True
