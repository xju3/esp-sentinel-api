from pydantic import BaseModel, Field
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

# New schemas for RMS report handling
class TriaxialValue(BaseModel):
    x: float
    y: float
    z: float
    m: float

class RmsReportBase(BaseModel):
    rms: TriaxialValue
    peak: TriaxialValue
    crest: TriaxialValue
    impulse: TriaxialValue
    temperature: float
    iso: int

class RmsReportCreate(RmsReportBase):
    sn: int
    event_type: int = Field(alias="et")
    timestamp: int = Field(alias="ts")

    class Config:
        orm_mode = True
        allow_population_by_field_name = True