from pydantic import BaseModel
from typing import Optional


class TriaxialValue(BaseModel):
    x: float
    y: float
    z: float
    m: float


class MachineStatus(BaseModel):
    rms: TriaxialValue
    st: int


class MachineData(BaseModel):
    sn: int
    et: int
    received_at: int
    status: Optional[MachineStatus] = None

# New schemas for RMS report handling

class RmsReportBase(BaseModel):
    rms: TriaxialValue
    peak: TriaxialValue
    crest: TriaxialValue
    impulse: TriaxialValue
    temperature: float
    iso: int

class RmsReportCreate(RmsReportBase):
    sn: int
    event_type: int
    timestamp: int

    class Config:
        orm_mode = True


class MachineStatusCreate(BaseModel):
    sn: int
    event_type: int
    rms: TriaxialValue
    st: int

    class Config:
        orm_mode = True
