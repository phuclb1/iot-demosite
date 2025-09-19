from db import Base
from sqlalchemy import Integer, Column, String, TIMESTAMP, func

class Device(Base):
    __tablename__ = "Devices"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True, unique=True)
    org = Column(String, index=True)
    site = Column(String, index=True)
    area = Column(String, index=True)
    installed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

