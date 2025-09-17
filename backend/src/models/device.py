"""
Device model for IoT Telemetry Dashboard.

Represents the fourth level in the organizational hierarchy:
Organization -> Sites -> Areas -> Devices

This model handles device metadata, status tracking, MAC addresses,
firmware versions, and relationships with areas and telemetry data.
"""

from datetime import datetime
from typing import List, Optional, Literal
from enum import Enum
import uuid
import re

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from .area import AreaTable


Base = declarative_base()


class DeviceStatus(str, Enum):
    """Device status enumeration."""
    ONLINE = "online"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"


class DeviceTable(Base):
    """SQLAlchemy table definition for devices."""

    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    area_id = Column(UUID(as_uuid=True), ForeignKey("areas.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    model = Column(String(255), nullable=False)
    firmware_version = Column(String(100), nullable=True)
    mac_address = Column(String(17), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(DeviceStatus), nullable=False, default=DeviceStatus.OFFLINE, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    area = relationship("AreaTable", back_populates="devices")

    def __repr__(self):
        return f"<Device(id={self.id}, name='{self.name}', model='{self.model}', status={self.status}, area_id={self.area_id})>"


class DeviceBase(BaseModel):
    """Base device model with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Device name or identifier")
    model: str = Field(..., min_length=1, max_length=255, description="Device model or type")
    firmware_version: Optional[str] = Field(None, max_length=100, description="Current firmware version")
    mac_address: Optional[str] = Field(None, description="Device MAC address")
    status: DeviceStatus = Field(default=DeviceStatus.OFFLINE, description="Current device status")

    @validator('name')
    def validate_name(cls, v):
        """Validate device name."""
        if not v.strip():
            raise ValueError('Device name cannot be empty or whitespace only')
        return v.strip()

    @validator('model')
    def validate_model(cls, v):
        """Validate device model."""
        if not v.strip():
            raise ValueError('Device model cannot be empty or whitespace only')
        return v.strip()

    @validator('firmware_version')
    def validate_firmware_version(cls, v):
        """Validate firmware version if provided."""
        if v is not None and not v.strip():
            return None  # Convert empty strings to None
        return v.strip() if v else v

    @validator('mac_address')
    def validate_mac_address(cls, v):
        """Validate MAC address format if provided."""
        if v is not None:
            if not v.strip():
                return None  # Convert empty strings to None

            v = v.strip()
            # MAC address pattern: XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX
            mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
            if not re.match(mac_pattern, v):
                raise ValueError('Invalid MAC address format. Expected format: XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX')

            # Normalize to colon format
            return v.replace('-', ':').upper()
        return v

    class Config:
        """Pydantic configuration."""
        str_strip_whitespace = True


class DeviceCreate(DeviceBase):
    """Model for creating a new device."""

    area_id: uuid.UUID = Field(..., description="Parent area ID")

    @validator('area_id')
    def validate_area_id(cls, v):
        """Validate area ID format."""
        if not isinstance(v, uuid.UUID):
            try:
                uuid.UUID(str(v))
            except ValueError:
                raise ValueError('Invalid area ID format')
        return v


class DeviceUpdate(BaseModel):
    """Model for updating a device."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    model: Optional[str] = Field(None, min_length=1, max_length=255)
    firmware_version: Optional[str] = Field(None, max_length=100)
    mac_address: Optional[str] = None
    status: Optional[DeviceStatus] = None

    @validator('name')
    def validate_name(cls, v):
        """Validate device name if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError('Device name cannot be empty or whitespace only')
            return v.strip()
        return v

    @validator('model')
    def validate_model(cls, v):
        """Validate device model if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError('Device model cannot be empty or whitespace only')
            return v.strip()
        return v

    @validator('firmware_version')
    def validate_firmware_version(cls, v):
        """Validate firmware version if provided."""
        if v is not None and not v.strip():
            return None  # Convert empty strings to None
        return v.strip() if v else v

    @validator('mac_address')
    def validate_mac_address(cls, v):
        """Validate MAC address format if provided."""
        if v is not None:
            if not v.strip():
                return None  # Convert empty strings to None

            v = v.strip()
            # MAC address pattern: XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX
            mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
            if not re.match(mac_pattern, v):
                raise ValueError('Invalid MAC address format. Expected format: XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX')

            # Normalize to colon format
            return v.replace('-', ':').upper()
        return v

    class Config:
        """Pydantic configuration."""
        str_strip_whitespace = True


class Device(DeviceBase):
    """Complete device model with all fields."""

    id: uuid.UUID = Field(..., description="Unique device identifier")
    area_id: uuid.UUID = Field(..., description="Parent area ID")
    last_seen: Optional[datetime] = Field(None, description="Last time device was seen")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z',
            uuid.UUID: str
        }


class DeviceWithHierarchy(Device):
    """Device model with full hierarchy context."""

    organization_name: str = Field(..., description="Organization name")
    organization_slug: str = Field(..., description="Organization slug")
    site_name: str = Field(..., description="Site name")
    site_slug: str = Field(..., description="Site slug")
    area_name: str = Field(..., description="Area name")
    area_slug: str = Field(..., description="Area slug")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class DeviceWithTelemetry(Device):
    """Device model with latest telemetry data."""

    latest_vibration: Optional[float] = Field(None, description="Latest vibration reading")
    latest_temperature: Optional[float] = Field(None, description="Latest temperature reading")
    latest_power: Optional[float] = Field(None, description="Latest power reading")
    latest_electricity: Optional[float] = Field(None, description="Latest electricity reading")
    latest_telemetry_timestamp: Optional[datetime] = Field(None, description="Latest telemetry timestamp")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class DeviceList(BaseModel):
    """Model for device list responses."""

    devices: List[Device] = Field(default_factory=list)
    total: int = Field(default=0, description="Total number of devices")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class DeviceStatusUpdate(BaseModel):
    """Model for updating device status."""

    status: DeviceStatus = Field(..., description="New device status")
    last_seen: Optional[datetime] = Field(None, description="Last seen timestamp")

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z'
        }


def get_device_models() -> List[dict]:
    """
    Get list of common device models for UI selection.

    Returns:
        List of device model dictionaries
    """
    device_models = [
        {"name": "vibration-sensor-v1", "label": "Vibration Sensor v1", "description": "Basic vibration monitoring sensor"},
        {"name": "vibration-sensor-v2", "label": "Vibration Sensor v2", "description": "Advanced vibration monitoring sensor"},
        {"name": "temperature-sensor", "label": "Temperature Sensor", "description": "Environmental temperature monitoring"},
        {"name": "power-meter", "label": "Power Meter", "description": "Electrical power consumption monitoring"},
        {"name": "multi-sensor-pro", "label": "Multi-Sensor Pro", "description": "Combined vibration, temperature, and power monitoring"},
        {"name": "iot-gateway", "label": "IoT Gateway", "description": "Data collection and transmission gateway"},
        {"name": "smart-meter", "label": "Smart Meter", "description": "Advanced electrical metering device"},
        {"name": "environmental-monitor", "label": "Environmental Monitor", "description": "Comprehensive environmental monitoring"},
        {"name": "custom-device", "label": "Custom Device", "description": "Custom or third-party device"}
    ]
    return device_models


def calculate_device_uptime(last_seen: Optional[datetime], status: DeviceStatus) -> Optional[float]:
    """
    Calculate device uptime percentage based on status and last seen.

    Args:
        last_seen: Last time device was seen
        status: Current device status

    Returns:
        Uptime percentage or None if cannot be calculated
    """
    if last_seen is None or status == DeviceStatus.MAINTENANCE:
        return None

    now = datetime.utcnow()
    time_since_seen = (now - last_seen).total_seconds()

    # Consider offline if not seen in last 10 minutes
    offline_threshold = 600  # 10 minutes

    if status == DeviceStatus.ONLINE and time_since_seen <= offline_threshold:
        return 100.0
    elif status == DeviceStatus.OFFLINE:
        return 0.0
    else:
        # Partial uptime based on last seen time
        uptime_percentage = max(0.0, 100.0 - (time_since_seen / offline_threshold * 100.0))
        return min(100.0, uptime_percentage)


def determine_device_status_from_telemetry(last_telemetry_time: Optional[datetime]) -> DeviceStatus:
    """
    Determine device status based on last telemetry timestamp.

    Args:
        last_telemetry_time: Timestamp of last telemetry data

    Returns:
        Inferred device status
    """
    if last_telemetry_time is None:
        return DeviceStatus.OFFLINE

    now = datetime.utcnow()
    time_since_telemetry = (now - last_telemetry_time).total_seconds()

    # Device is considered offline if no telemetry for 10 minutes
    offline_threshold = 600  # 10 minutes

    if time_since_telemetry <= offline_threshold:
        return DeviceStatus.ONLINE
    else:
        return DeviceStatus.OFFLINE


def validate_device_access(user_org_permissions: List[str], organization_id: str) -> bool:
    """
    Validate if user has permission to access device through organization.

    Args:
        user_org_permissions: List of organization IDs user has access to
        organization_id: Organization ID that owns the device's area's site

    Returns:
        True if user has access, False otherwise
    """
    return organization_id in user_org_permissions


def build_device_hierarchy_path(organization_slug: str, site_slug: str, area_slug: str, device_name: str) -> str:
    """
    Build hierarchical path for device.

    Args:
        organization_slug: Organization slug
        site_slug: Site slug
        area_slug: Area slug
        device_name: Device name

    Returns:
        Hierarchical path string

    Example:
        build_device_hierarchy_path("acme-corp", "factory-01", "production-floor", "sensor-001")
        -> "acme-corp/factory-01/production-floor/sensor-001"
    """
    return f"{organization_slug}/{site_slug}/{area_slug}/{device_name}"


class DeviceRepository:
    """Repository pattern for device data access."""

    def __init__(self, db_session):
        """Initialize repository with database session."""
        self.db = db_session

    async def get_by_id(self, device_id: uuid.UUID) -> Optional[DeviceTable]:
        """Get device by ID."""
        # Implementation would use actual database query
        pass

    async def get_by_area(self, area_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[DeviceTable]:
        """Get all devices in an area with pagination."""
        # Implementation would use actual database query
        pass

    async def get_by_organization(self, org_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[DeviceTable]:
        """Get all devices in an organization with pagination."""
        # Implementation would use actual database query with joins
        pass

    async def get_by_status(self, status: DeviceStatus, org_id: Optional[uuid.UUID] = None) -> List[DeviceTable]:
        """Get devices by status, optionally filtered by organization."""
        # Implementation would use actual database query
        pass

    async def create(self, device_data: DeviceCreate) -> DeviceTable:
        """Create new device."""
        # Implementation would use actual database query
        pass

    async def update(self, device_id: uuid.UUID, device_data: DeviceUpdate) -> Optional[DeviceTable]:
        """Update device."""
        # Implementation would use actual database query
        pass

    async def update_status(self, device_id: uuid.UUID, status_data: DeviceStatusUpdate) -> Optional[DeviceTable]:
        """Update device status and last seen."""
        # Implementation would use actual database query
        pass

    async def delete(self, device_id: uuid.UUID) -> bool:
        """Delete device."""
        # Implementation would use actual database query
        pass

    async def get_with_hierarchy(self, device_id: uuid.UUID) -> Optional[dict]:
        """Get device with full hierarchy context."""
        # Implementation would use actual database query with joins
        pass

    async def get_with_telemetry(self, device_id: uuid.UUID) -> Optional[dict]:
        """Get device with latest telemetry data."""
        # Implementation would use actual database query with joins to InfluxDB
        pass

    async def count_by_area(self, area_id: uuid.UUID) -> int:
        """Count devices in area."""
        # Implementation would use actual database query
        pass

    async def count_by_organization(self, org_id: uuid.UUID) -> int:
        """Count devices in organization."""
        # Implementation would use actual database query with joins
        pass

    async def count_by_status(self, status: DeviceStatus, org_id: Optional[uuid.UUID] = None) -> int:
        """Count devices by status."""
        # Implementation would use actual database query
        pass

    async def search_by_name(self, search_term: str, org_id: Optional[uuid.UUID] = None, limit: int = 50) -> List[DeviceTable]:
        """Search devices by name."""
        # Implementation would use actual database query with text search
        pass

    async def get_by_mac_address(self, mac_address: str) -> Optional[DeviceTable]:
        """Get device by MAC address."""
        # Implementation would use actual database query
        pass

    async def update_last_seen_batch(self, device_ids: List[uuid.UUID], timestamp: datetime) -> int:
        """Update last seen timestamp for multiple devices."""
        # Implementation would use actual database query with bulk update
        pass