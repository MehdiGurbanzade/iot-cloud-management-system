from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Device(BaseModel):
    id: Optional[int] = None
    device_name: str
    location: str
    is_active: bool = True


class SensorData(BaseModel):
    device_id: str
    temperature: float
    humidity: float
    # IMPORTANT: default_factory makes sure timestamp is evaluated per-request (not once at import time)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
