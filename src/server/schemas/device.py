from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class DeviceStatus(str, Enum):
    FREE = "free"
    RESERVED = "reserved"
    RUNNING = "running"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"

class Device(BaseModel):
    id: str
    type: str = "adb"
    model: str | None = None
    remark: str | None = None  # User-defined note for easier identification
    status: DeviceStatus = DeviceStatus.FREE
    last_heartbeat: datetime | None = None
    locked_by: str | None = None  # run_id or user
    battery: int | None = None
