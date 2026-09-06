from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: int
    timestamp: datetime
    user_id: Optional[int] = None
    action: str
    file_id: Optional[int] = None
    query: Optional[str] = None
    details: Optional[str] = None

    class Config:
        from_attributes = True
