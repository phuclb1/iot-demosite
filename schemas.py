from pydantic import BaseModel
from datetime import datetime

class DeviceBase(BaseModel):
    id : int
    device_id : str
    org : str
    site : str
    area : str
    installed_at : datetime

class Data(BaseModel):
    device_id: str
    temperature: float
    rms_x: float
    rms_y: float
    rms_z: float
    peak_x: float
    peak_z: float
    battery_v: float
    rssi_dbm: float
    timestamp: datetime = None

class DeviceCreate(DeviceBase):
    pass 

class DeviceUpdate(DeviceBase):
    pass 

class DeviceRead(DeviceBase):
    pass 

class DeviceRead(DeviceBase): 
    pass 

class Config:
    orm_mode = True