from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MachineStatus(BaseModel):
    x: float
    y: float
    z: float
    m: float
    st: int

class MachineData(BaseModel):
    sn: int
    et: int
    ts: int
    received_at: int
    status: Optional[MachineStatus] = None