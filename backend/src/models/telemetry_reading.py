"""
TelemetryReading model for IoT Telemetry Dashboard.

Represents time-series telemetry data from IoT devices stored in InfluxDB.
Handles vibration, temperature, power, and electricity measurements
with organizational hierarchy context.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
import uuid

from pydantic import BaseModel, Field, validator


class TelemetryReading(BaseModel):
    """Model for individual telemetry reading from IoT device."""

    device_id: uuid.UUID = Field(..., description="Device identifier")
    vibration: float = Field(..., description="Vibration measurement (Hz or g-force)")
    temperature: float = Field(..., description="Temperature measurement (Celsius)")
    power: float = Field(..., description="Power consumption (Watts)")
    electricity: float = Field(..., description="Electrical measurement (Amps, Voltage, etc.)")
    timestamp: datetime = Field(..., description="Measurement timestamp")
    org: str = Field(..., description="Organization slug")
    site: str = Field(..., description="Site slug")
    area: str = Field(..., description="Area slug")

    @validator('device_id')
    def validate_device_id(cls, v):
        """Validate device ID format."""
        if not isinstance(v, uuid.UUID):
            try:
                uuid.UUID(str(v))
            except ValueError:
                raise ValueError('Invalid device ID format')
        return v

    @validator('vibration')
    def validate_vibration(cls, v):
        """Validate vibration measurement."""
        if v < 0:
            raise ValueError('Vibration cannot be negative')
        if v > 1000:  # Reasonable upper limit
            raise ValueError('Vibration value seems unrealistic (>1000)')
        return v

    @validator('temperature')
    def validate_temperature(cls, v):
        """Validate temperature measurement."""
        if v < -273.15:  # Absolute zero
            raise ValueError('Temperature cannot be below absolute zero')
        if v > 1000:  # Reasonable upper limit for industrial environments
            raise ValueError('Temperature value seems unrealistic (>1000°C)')
        return v

    @validator('power')
    def validate_power(cls, v):
        """Validate power measurement."""
        if v < 0:
            raise ValueError('Power cannot be negative')
        if v > 1000000:  # 1MW upper limit
            raise ValueError('Power value seems unrealistic (>1MW)')
        return v

    @validator('electricity')
    def validate_electricity(cls, v):
        """Validate electricity measurement."""
        if v < 0:
            raise ValueError('Electricity measurement cannot be negative')
        if v > 10000:  # Reasonable upper limit
            raise ValueError('Electricity value seems unrealistic (>10000)')
        return v

    @validator('org', 'site', 'area')
    def validate_slug_fields(cls, v):
        """Validate slug format for hierarchy fields."""
        if not v or not v.strip():
            raise ValueError('Hierarchy slug cannot be empty')

        import re
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')

        return v.strip()

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z',
            uuid.UUID: str
        }


class TelemetryReadingCreate(BaseModel):
    """Model for creating telemetry readings from MQTT messages."""

    device_id: uuid.UUID = Field(..., description="Device identifier")
    vibration: float = Field(..., description="Vibration measurement")
    temperature: float = Field(..., description="Temperature measurement")
    power: float = Field(..., description="Power consumption")
    electricity: float = Field(..., description="Electrical measurement")
    timestamp: Optional[datetime] = Field(None, description="Measurement timestamp (defaults to now)")
    org: str = Field(..., description="Organization slug")
    site: str = Field(..., description="Site slug")
    area: str = Field(..., description="Area slug")

    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        """Set timestamp to now if not provided."""
        return v or datetime.utcnow()

    # Inherit validators from TelemetryReading
    _validate_device_id = validator('device_id', allow_reuse=True)(TelemetryReading.validate_device_id)
    _validate_vibration = validator('vibration', allow_reuse=True)(TelemetryReading.validate_vibration)
    _validate_temperature = validator('temperature', allow_reuse=True)(TelemetryReading.validate_temperature)
    _validate_power = validator('power', allow_reuse=True)(TelemetryReading.validate_power)
    _validate_electricity = validator('electricity', allow_reuse=True)(TelemetryReading.validate_electricity)
    _validate_slugs = validator('org', 'site', 'area', allow_reuse=True)(TelemetryReading.validate_slug_fields)


class TelemetryHistoricalQuery(BaseModel):
    """Model for querying historical telemetry data."""

    device_id: uuid.UUID = Field(..., description="Device identifier")
    start: datetime = Field(..., description="Start time (inclusive)")
    end: datetime = Field(..., description="End time (inclusive)")
    interval: str = Field(default="1s", description="Aggregation interval")

    @validator('interval')
    def validate_interval(cls, v):
        """Validate aggregation interval."""
        valid_intervals = ["1s", "5s", "30s", "1m", "5m", "1h"]
        if v not in valid_intervals:
            raise ValueError(f'Invalid interval. Must be one of: {", ".join(valid_intervals)}')
        return v

    @validator('end')
    def validate_time_range(cls, v, values):
        """Validate that end time is after start time."""
        if 'start' in values and v <= values['start']:
            raise ValueError('End time must be after start time')
        return v

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z',
            uuid.UUID: str
        }


class TelemetryHistoricalResponse(BaseModel):
    """Model for historical telemetry query response."""

    data: List[TelemetryReading] = Field(default_factory=list, description="Telemetry readings")
    total: int = Field(..., description="Total number of readings")
    interval: str = Field(..., description="Aggregation interval used")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class TelemetryStreamFilter(BaseModel):
    """Model for filtering real-time telemetry stream."""

    devices: Optional[List[uuid.UUID]] = Field(None, description="Device IDs to include")
    organizations: Optional[List[str]] = Field(None, description="Organization slugs to include")

    @validator('devices', pre=True)
    def parse_devices(cls, v):
        """Parse comma-separated device IDs."""
        if isinstance(v, str):
            if not v.strip():
                return None
            device_ids = []
            for device_str in v.split(','):
                device_str = device_str.strip()
                if device_str:
                    try:
                        device_ids.append(uuid.UUID(device_str))
                    except ValueError:
                        raise ValueError(f'Invalid device ID format: {device_str}')
            return device_ids if device_ids else None
        return v

    @validator('organizations', pre=True)
    def parse_organizations(cls, v):
        """Parse comma-separated organization slugs."""
        if isinstance(v, str):
            if not v.strip():
                return None
            org_slugs = []
            for org_str in v.split(','):
                org_str = org_str.strip()
                if org_str:
                    org_slugs.append(org_str)
            return org_slugs if org_slugs else None
        return v

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            uuid.UUID: str
        }


class TelemetryAggregation(BaseModel):
    """Model for aggregated telemetry statistics."""

    device_id: uuid.UUID = Field(..., description="Device identifier")
    start_time: datetime = Field(..., description="Aggregation window start")
    end_time: datetime = Field(..., description="Aggregation window end")
    avg_vibration: float = Field(..., description="Average vibration")
    min_vibration: float = Field(..., description="Minimum vibration")
    max_vibration: float = Field(..., description="Maximum vibration")
    avg_temperature: float = Field(..., description="Average temperature")
    min_temperature: float = Field(..., description="Minimum temperature")
    max_temperature: float = Field(..., description="Maximum temperature")
    avg_power: float = Field(..., description="Average power")
    min_power: float = Field(..., description="Minimum power")
    max_power: float = Field(..., description="Maximum power")
    avg_electricity: float = Field(..., description="Average electricity")
    min_electricity: float = Field(..., description="Minimum electricity")
    max_electricity: float = Field(..., description="Maximum electricity")
    reading_count: int = Field(..., description="Number of readings in aggregation")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z',
            uuid.UUID: str
        }


def validate_telemetry_thresholds(reading: TelemetryReading) -> Dict[str, bool]:
    """
    Validate telemetry reading against predefined thresholds.

    Args:
        reading: Telemetry reading to validate

    Returns:
        Dictionary of threshold violation flags
    """
    # These thresholds would typically be configurable per device/organization
    thresholds = {
        'vibration_max': 10.0,
        'temperature_max': 80.0,
        'power_max': 1000.0,
        'electricity_max': 100.0
    }

    violations = {
        'vibration_exceeded': reading.vibration > thresholds['vibration_max'],
        'temperature_exceeded': reading.temperature > thresholds['temperature_max'],
        'power_exceeded': reading.power > thresholds['power_max'],
        'electricity_exceeded': reading.electricity > thresholds['electricity_max']
    }

    return violations


def convert_to_influxdb_point(reading: TelemetryReadingCreate) -> Dict[str, Any]:
    """
    Convert telemetry reading to InfluxDB point format.

    Args:
        reading: Telemetry reading to convert

    Returns:
        InfluxDB point dictionary
    """
    return {
        "measurement": "telemetry",
        "tags": {
            "device_id": str(reading.device_id),
            "org": reading.org,
            "site": reading.site,
            "area": reading.area
        },
        "fields": {
            "vibration": reading.vibration,
            "temperature": reading.temperature,
            "power": reading.power,
            "electricity": reading.electricity
        },
        "time": reading.timestamp
    }


def convert_from_influxdb_point(point: Dict[str, Any]) -> TelemetryReading:
    """
    Convert InfluxDB point to telemetry reading.

    Args:
        point: InfluxDB point dictionary

    Returns:
        TelemetryReading object
    """
    return TelemetryReading(
        device_id=uuid.UUID(point["tags"]["device_id"]),
        vibration=point["fields"]["vibration"],
        temperature=point["fields"]["temperature"],
        power=point["fields"]["power"],
        electricity=point["fields"]["electricity"],
        timestamp=point["time"],
        org=point["tags"]["org"],
        site=point["tags"]["site"],
        area=point["tags"]["area"]
    )


def build_influxdb_query(query: TelemetryHistoricalQuery) -> str:
    """
    Build InfluxDB query string for historical data.

    Args:
        query: Historical query parameters

    Returns:
        InfluxDB query string
    """
    start_time = query.start.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time = query.end.strftime('%Y-%m-%dT%H:%M:%SZ')

    if query.interval == "1s":
        # No aggregation for 1-second interval
        influx_query = f"""
        SELECT vibration, temperature, power, electricity
        FROM telemetry
        WHERE device_id = '{query.device_id}'
        AND time >= '{start_time}'
        AND time <= '{end_time}'
        ORDER BY time ASC
        """
    else:
        # Aggregate data for other intervals
        influx_query = f"""
        SELECT MEAN(vibration) as vibration,
               MEAN(temperature) as temperature,
               MEAN(power) as power,
               MEAN(electricity) as electricity
        FROM telemetry
        WHERE device_id = '{query.device_id}'
        AND time >= '{start_time}'
        AND time <= '{end_time}'
        GROUP BY time({query.interval})
        ORDER BY time ASC
        """

    return influx_query.strip()


class TelemetryRepository:
    """Repository pattern for telemetry data access."""

    def __init__(self, influxdb_client):
        """Initialize repository with InfluxDB client."""
        self.influxdb = influxdb_client

    async def write_reading(self, reading: TelemetryReadingCreate) -> bool:
        """Write single telemetry reading to InfluxDB."""
        # Implementation would use actual InfluxDB client
        pass

    async def write_readings_batch(self, readings: List[TelemetryReadingCreate]) -> int:
        """Write multiple telemetry readings to InfluxDB."""
        # Implementation would use actual InfluxDB client
        pass

    async def get_current(self, device_id: uuid.UUID) -> Optional[TelemetryReading]:
        """Get most recent telemetry reading for device."""
        # Implementation would use actual InfluxDB client
        pass

    async def get_historical(self, query: TelemetryHistoricalQuery) -> TelemetryHistoricalResponse:
        """Get historical telemetry data for device."""
        # Implementation would use actual InfluxDB client
        pass

    async def get_aggregation(self, device_id: uuid.UUID, start: datetime, end: datetime) -> Optional[TelemetryAggregation]:
        """Get aggregated telemetry statistics for device."""
        # Implementation would use actual InfluxDB client
        pass

    async def get_devices_with_recent_data(self, org_id: Optional[str] = None, minutes: int = 10) -> List[uuid.UUID]:
        """Get list of devices with recent telemetry data."""
        # Implementation would use actual InfluxDB client
        pass

    async def delete_device_data(self, device_id: uuid.UUID, start: Optional[datetime] = None, end: Optional[datetime] = None) -> bool:
        """Delete telemetry data for device."""
        # Implementation would use actual InfluxDB client
        pass

    async def get_latest_by_organization(self, org_slug: str, limit: int = 100) -> List[TelemetryReading]:
        """Get latest telemetry readings for organization."""
        # Implementation would use actual InfluxDB client
        pass