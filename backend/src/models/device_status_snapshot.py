"""
DeviceStatusSnapshot model for IoT Telemetry Dashboard.

Represents time-series device status data stored in InfluxDB.
Tracks device connectivity, uptime, and operational status over time
for monitoring and analytics purposes.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid

from pydantic import BaseModel, Field, validator

from .device import DeviceStatus


class DeviceStatusSnapshot(BaseModel):
    """Model for device status snapshot stored in time-series database."""

    device_id: uuid.UUID = Field(..., description="Device identifier")
    status: DeviceStatus = Field(..., description="Device status at this point in time")
    uptime_seconds: int = Field(..., description="Device uptime in seconds since last restart")
    last_seen_timestamp: int = Field(..., description="Unix timestamp when device was last seen")
    connection_count: int = Field(default=1, description="Number of active connections")
    timestamp: datetime = Field(..., description="Snapshot timestamp")
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

    @validator('uptime_seconds')
    def validate_uptime(cls, v):
        """Validate uptime value."""
        if v < 0:
            raise ValueError('Uptime cannot be negative')
        if v > 31536000:  # 1 year in seconds
            raise ValueError('Uptime seems unrealistic (>1 year)')
        return v

    @validator('last_seen_timestamp')
    def validate_last_seen_timestamp(cls, v):
        """Validate last seen timestamp."""
        if v < 0:
            raise ValueError('Last seen timestamp cannot be negative')
        # Check if timestamp is not too far in the future (allow 1 hour tolerance)
        now_timestamp = int(datetime.utcnow().timestamp())
        if v > now_timestamp + 3600:
            raise ValueError('Last seen timestamp cannot be more than 1 hour in the future')
        return v

    @validator('connection_count')
    def validate_connection_count(cls, v):
        """Validate connection count."""
        if v < 0:
            raise ValueError('Connection count cannot be negative')
        if v > 100:  # Reasonable upper limit
            raise ValueError('Connection count seems unrealistic (>100)')
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


class DeviceStatusSnapshotCreate(BaseModel):
    """Model for creating device status snapshots."""

    device_id: uuid.UUID = Field(..., description="Device identifier")
    status: DeviceStatus = Field(..., description="Device status")
    uptime_seconds: int = Field(..., description="Device uptime in seconds")
    last_seen_timestamp: Optional[int] = Field(None, description="Last seen timestamp (defaults to now)")
    connection_count: int = Field(default=1, description="Number of active connections")
    timestamp: Optional[datetime] = Field(None, description="Snapshot timestamp (defaults to now)")
    org: str = Field(..., description="Organization slug")
    site: str = Field(..., description="Site slug")
    area: str = Field(..., description="Area slug")

    @validator('timestamp', pre=True, always=True)
    def set_timestamp(cls, v):
        """Set timestamp to now if not provided."""
        return v or datetime.utcnow()

    @validator('last_seen_timestamp', pre=True, always=True)
    def set_last_seen_timestamp(cls, v):
        """Set last seen timestamp to now if not provided."""
        return v or int(datetime.utcnow().timestamp())

    # Inherit validators from DeviceStatusSnapshot
    _validate_device_id = validator('device_id', allow_reuse=True)(DeviceStatusSnapshot.validate_device_id)
    _validate_uptime = validator('uptime_seconds', allow_reuse=True)(DeviceStatusSnapshot.validate_uptime)
    _validate_last_seen = validator('last_seen_timestamp', allow_reuse=True)(DeviceStatusSnapshot.validate_last_seen_timestamp)
    _validate_connection_count = validator('connection_count', allow_reuse=True)(DeviceStatusSnapshot.validate_connection_count)
    _validate_slugs = validator('org', 'site', 'area', allow_reuse=True)(DeviceStatusSnapshot.validate_slug_fields)


class DeviceStatusHistoricalQuery(BaseModel):
    """Model for querying historical device status data."""

    device_id: uuid.UUID = Field(..., description="Device identifier")
    start: datetime = Field(..., description="Start time (inclusive)")
    end: datetime = Field(..., description="End time (inclusive)")
    interval: str = Field(default="5m", description="Aggregation interval")

    @validator('interval')
    def validate_interval(cls, v):
        """Validate aggregation interval."""
        valid_intervals = ["1m", "5m", "15m", "1h", "6h", "1d"]
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


class DeviceStatusHistoricalResponse(BaseModel):
    """Model for historical device status query response."""

    data: List[DeviceStatusSnapshot] = Field(default_factory=list, description="Status snapshots")
    total: int = Field(..., description="Total number of snapshots")
    interval: str = Field(..., description="Aggregation interval used")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class DeviceUptimeReport(BaseModel):
    """Model for device uptime report."""

    device_id: uuid.UUID = Field(..., description="Device identifier")
    start_time: datetime = Field(..., description="Report period start")
    end_time: datetime = Field(..., description="Report period end")
    total_uptime_seconds: int = Field(..., description="Total uptime in seconds")
    total_downtime_seconds: int = Field(..., description="Total downtime in seconds")
    uptime_percentage: float = Field(..., description="Uptime percentage")
    status_changes: int = Field(..., description="Number of status changes")
    avg_uptime_per_session: float = Field(..., description="Average uptime per session in seconds")
    longest_uptime_session: int = Field(..., description="Longest continuous uptime in seconds")
    longest_downtime_session: int = Field(..., description="Longest continuous downtime in seconds")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z',
            uuid.UUID: str
        }


class DeviceStatusAggregation(BaseModel):
    """Model for aggregated device status statistics."""

    device_id: uuid.UUID = Field(..., description="Device identifier")
    start_time: datetime = Field(..., description="Aggregation window start")
    end_time: datetime = Field(..., description="Aggregation window end")
    avg_uptime_seconds: float = Field(..., description="Average uptime")
    min_uptime_seconds: int = Field(..., description="Minimum uptime")
    max_uptime_seconds: int = Field(..., description="Maximum uptime")
    avg_connection_count: float = Field(..., description="Average connection count")
    online_percentage: float = Field(..., description="Percentage of time online")
    offline_percentage: float = Field(..., description="Percentage of time offline")
    maintenance_percentage: float = Field(..., description="Percentage of time in maintenance")
    snapshot_count: int = Field(..., description="Number of snapshots in aggregation")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z',
            uuid.UUID: str
        }


def calculate_uptime_from_last_restart(last_restart: datetime, current_time: Optional[datetime] = None) -> int:
    """
    Calculate device uptime in seconds from last restart.

    Args:
        last_restart: When device was last restarted
        current_time: Current time (defaults to now)

    Returns:
        Uptime in seconds
    """
    if current_time is None:
        current_time = datetime.utcnow()

    if last_restart > current_time:
        raise ValueError('Last restart cannot be in the future')

    uptime_delta = current_time - last_restart
    return int(uptime_delta.total_seconds())


def determine_status_from_last_seen(last_seen_timestamp: int, current_timestamp: Optional[int] = None) -> DeviceStatus:
    """
    Determine device status based on last seen timestamp.

    Args:
        last_seen_timestamp: Unix timestamp when device was last seen
        current_timestamp: Current timestamp (defaults to now)

    Returns:
        Inferred device status
    """
    if current_timestamp is None:
        current_timestamp = int(datetime.utcnow().timestamp())

    time_since_seen = current_timestamp - last_seen_timestamp

    # Device is considered offline if not seen in last 10 minutes
    offline_threshold = 600  # 10 minutes

    if time_since_seen <= offline_threshold:
        return DeviceStatus.ONLINE
    else:
        return DeviceStatus.OFFLINE


def convert_to_influxdb_point(snapshot: DeviceStatusSnapshotCreate) -> Dict[str, Any]:
    """
    Convert device status snapshot to InfluxDB point format.

    Args:
        snapshot: Status snapshot to convert

    Returns:
        InfluxDB point dictionary
    """
    return {
        "measurement": "device_status",
        "tags": {
            "device_id": str(snapshot.device_id),
            "status": snapshot.status.value,
            "org": snapshot.org,
            "site": snapshot.site,
            "area": snapshot.area
        },
        "fields": {
            "uptime_seconds": snapshot.uptime_seconds,
            "last_seen_timestamp": snapshot.last_seen_timestamp,
            "connection_count": snapshot.connection_count
        },
        "time": snapshot.timestamp
    }


def convert_from_influxdb_point(point: Dict[str, Any]) -> DeviceStatusSnapshot:
    """
    Convert InfluxDB point to device status snapshot.

    Args:
        point: InfluxDB point dictionary

    Returns:
        DeviceStatusSnapshot object
    """
    return DeviceStatusSnapshot(
        device_id=uuid.UUID(point["tags"]["device_id"]),
        status=DeviceStatus(point["tags"]["status"]),
        uptime_seconds=point["fields"]["uptime_seconds"],
        last_seen_timestamp=point["fields"]["last_seen_timestamp"],
        connection_count=point["fields"]["connection_count"],
        timestamp=point["time"],
        org=point["tags"]["org"],
        site=point["tags"]["site"],
        area=point["tags"]["area"]
    )


def build_influxdb_status_query(query: DeviceStatusHistoricalQuery) -> str:
    """
    Build InfluxDB query string for historical status data.

    Args:
        query: Historical query parameters

    Returns:
        InfluxDB query string
    """
    start_time = query.start.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time = query.end.strftime('%Y-%m-%dT%H:%M:%SZ')

    influx_query = f"""
    SELECT LAST(uptime_seconds) as uptime_seconds,
           LAST(last_seen_timestamp) as last_seen_timestamp,
           LAST(connection_count) as connection_count,
           LAST(status) as status
    FROM device_status
    WHERE device_id = '{query.device_id}'
    AND time >= '{start_time}'
    AND time <= '{end_time}'
    GROUP BY time({query.interval}), status
    ORDER BY time ASC
    """

    return influx_query.strip()


def calculate_device_uptime_percentage(snapshots: List[DeviceStatusSnapshot]) -> float:
    """
    Calculate uptime percentage from status snapshots.

    Args:
        snapshots: List of status snapshots ordered by time

    Returns:
        Uptime percentage (0-100)
    """
    if not snapshots or len(snapshots) < 2:
        return 0.0

    total_time = 0
    uptime = 0

    for i in range(len(snapshots) - 1):
        current_snapshot = snapshots[i]
        next_snapshot = snapshots[i + 1]

        # Calculate time between snapshots
        time_delta = (next_snapshot.timestamp - current_snapshot.timestamp).total_seconds()
        total_time += time_delta

        # If current status is online, add to uptime
        if current_snapshot.status == DeviceStatus.ONLINE:
            uptime += time_delta

    if total_time == 0:
        return 0.0

    return (uptime / total_time) * 100.0


class DeviceStatusRepository:
    """Repository pattern for device status data access."""

    def __init__(self, influxdb_client):
        """Initialize repository with InfluxDB client."""
        self.influxdb = influxdb_client

    async def write_snapshot(self, snapshot: DeviceStatusSnapshotCreate) -> bool:
        """Write device status snapshot to InfluxDB."""
        # Implementation would use actual InfluxDB client
        pass

    async def write_snapshots_batch(self, snapshots: List[DeviceStatusSnapshotCreate]) -> int:
        """Write multiple status snapshots to InfluxDB."""
        # Implementation would use actual InfluxDB client
        pass

    async def get_latest_status(self, device_id: uuid.UUID) -> Optional[DeviceStatusSnapshot]:
        """Get most recent status snapshot for device."""
        # Implementation would use actual InfluxDB client
        pass

    async def get_historical_status(self, query: DeviceStatusHistoricalQuery) -> DeviceStatusHistoricalResponse:
        """Get historical status data for device."""
        # Implementation would use actual InfluxDB client
        pass

    async def get_uptime_report(self, device_id: uuid.UUID, start: datetime, end: datetime) -> DeviceUptimeReport:
        """Get uptime report for device."""
        # Implementation would use actual InfluxDB client
        pass

    async def get_status_aggregation(self, device_id: uuid.UUID, start: datetime, end: datetime) -> Optional[DeviceStatusAggregation]:
        """Get aggregated status statistics for device."""
        # Implementation would use actual InfluxDB client
        pass

    async def get_devices_by_current_status(self, status: DeviceStatus, org_slug: Optional[str] = None) -> List[uuid.UUID]:
        """Get list of devices with specific current status."""
        # Implementation would use actual InfluxDB client
        pass

    async def delete_device_status_data(self, device_id: uuid.UUID, start: Optional[datetime] = None, end: Optional[datetime] = None) -> bool:
        """Delete status data for device."""
        # Implementation would use actual InfluxDB client
        pass

    async def get_organization_status_summary(self, org_slug: str, time_window_hours: int = 24) -> Dict[str, int]:
        """Get organization-wide device status summary."""
        # Implementation would use actual InfluxDB client
        pass