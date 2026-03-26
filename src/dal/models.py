from sqlalchemy import Column, Integer, String, Float, BigInteger, DateTime
from sqlalchemy.sql import func
from src.dal.database import Base

class MachineEvent(Base):
    __tablename__ = "machine_events"

    id = Column(Integer, primary_key=True, index=True)
    
    # Metadata from MsgPayload
    sn = Column(Integer, index=True, comment="设备序列号")
    event_type = Column(Integer, comment="事件类型")
    timestamp = Column(BigInteger, index=True, comment="Unix时间戳 (ms)")
    
    # RMS values from MsgTriaxialValue
    rms_x = Column(Float)
    rms_y = Column(Float)
    rms_z = Column(Float)
    rms_m = Column(Float)
    
    # Peak values
    peak_x = Column(Float)
    peak_y = Column(Float)
    peak_z = Column(Float)
    peak_m = Column(Float)
    
    # Crest values
    crest_x = Column(Float)
    crest_y = Column(Float)
    crest_z = Column(Float)
    crest_m = Column(Float)
    
    # Impulse values
    impulse_x = Column(Float)
    impulse_y = Column(Float)
    impulse_z = Column(Float)
    impulse_m = Column(Float)
    
    # Other fields
    temperature = Column(Float)
    iso = Column(Integer, comment="ISO标准")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
