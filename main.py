from typing import Union, Optional
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client .client.write_api import SYNCHRONOUS
from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
import models, schemas
from db import engine, Base, get_db
from sqlalchemy.orm import Session

app = FastAPI()

url = "http://localhost:8086"
token = "rwxEeiKenR5FgR6j6ZdCiTpc-4EERx9rQ53D9_DUgyNBapQdDSvgEg36knJ9NdbOaMT8K8_pnP2GEjzG-bAwgg=="
org = "test_org"
bucket = "machine_monitoring"


client = InfluxDBClient(url=url, token=token, org=org)
write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()



@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.post("/write_telemetry")
async def write_data(data: schemas.Data):
    point = Point("vibration_telemetry") \
    .tag("device_id", data.device_id) \
    .field("temperature", data.temperature) \
    .field("rm_x", data.rms_x) \
    .field("rm_y", data.rms_y) \
    .field("rm_z", data.rms_z) \
    .field("peak_x", data.peak_x) \
    .field("peak_z", data.peak_z) \
    .field("battery_v", data.battery_v) \
    .field("rssi_dbm", data.rssi_dbm)

    if data.timestamp:
        point = point.time(data.timestamp)

    write_api.write(bucket=bucket, record=point)
    return {"message": "Data written successfully"}

@app.get("/get_telemetry")
async def get_data(
    start: str = Query("-1h", description="Time range start"),
    device_id: str = Query(..., description="Device name"),
    field: str = Query(..., description="Field name")
    ):

    query = f'''
    from(bucket: "{bucket}")
    |> range(start: {start})
    |> filter(fn: (r) => r.device_id == "{device_id}")
    |> filter(fn: (r) => r._field == "{field}")
    '''
    tables = query_api.query(query, org=org)
    results = []
    for table in tables:
        for record in table.records:
            results.append({
                "time": record.get_time().isoformat(),
                "value": record.get_value()
            })

    return {"data": results}


@app.post("/devices", response_model=schemas.DeviceRead)
def create_device(item: schemas.DeviceCreate, db: Session = Depends(get_db)):
    db_item = models.Device(
                            id = item.id,
                            device_id = item.device_id, 
                            org = item.org,
                            site = item.site,
                            area = item.area,
                            installed_at = item.installed_at
                            )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@app.get("/devices/{device_id}", response_model=schemas.DeviceRead)
def read_device(device_id: str, db: Session = Depends(get_db)):
    device = db.query(models.Device).filter(models.Device.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Item not found")
    return device
