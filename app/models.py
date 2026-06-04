# Database models and Pydantic event schemas
from pydantic import BaseModel
from typing import Optional, Dict, Any

class EventModel(BaseModel):
    event_id: str
    store_id: str
    camera_id: str
    visitor_id: str
    event_type: str
    timestamp: str
    zone_id: Optional[str] = None
    dwell_ms: Optional[int] = 0
    is_staff: Optional[bool] = False
    confidence: Optional[float] = 1.0
    metadata: Optional[Dict[str, Any]] = None
