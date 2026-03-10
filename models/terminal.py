from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TerminalDevice(BaseModel):
    terminal_id: str
    charger_id: str
    connector_id: int
    location_id: Optional[str] = None
    status: str = 'ACTIVE'
    created_at: datetime
    updated_at: datetime
