"""
Site model for IoT Telemetry Dashboard.

Represents the second level in the organizational hierarchy:
Organization -> Sites -> Areas -> Devices

This model handles site metadata, timezone management,
and relationships with organizations and areas.
"""

from datetime import datetime
from typing import List, Optional
import uuid
import re
import pytz

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from .organization import OrganizationTable


Base = declarative_base()


class SiteTable(Base):
    """SQLAlchemy table definition for sites."""

    __tablename__ = "sites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    timezone = Column(String(50), nullable=False, default="UTC")
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("OrganizationTable", back_populates="sites")
    areas = relationship("AreaTable", back_populates="site", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Site(id={self.id}, name='{self.name}', slug='{self.slug}', org_id={self.organization_id})>"


class SiteBase(BaseModel):
    """Base site model with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Site name")
    slug: str = Field(..., min_length=1, max_length=255, description="URL-safe site identifier within organization")
    location: Optional[str] = Field(None, max_length=255, description="Physical location or address")
    timezone: str = Field(default="UTC", description="Site timezone (IANA timezone name)")

    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format: lowercase letters, numbers, hyphens only."""
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        if v.startswith('-') or v.endswith('-'):
            raise ValueError('Slug cannot start or end with a hyphen')
        if '--' in v:
            raise ValueError('Slug cannot contain consecutive hyphens')
        return v

    @validator('name')
    def validate_name(cls, v):
        """Validate site name."""
        if not v.strip():
            raise ValueError('Site name cannot be empty or whitespace only')
        return v.strip()

    @validator('timezone')
    def validate_timezone(cls, v):
        """Validate timezone is a valid IANA timezone."""
        try:
            pytz.timezone(v)
        except pytz.exceptions.UnknownTimeZoneError:
            raise ValueError(f'Invalid timezone: {v}')
        return v

    @validator('location')
    def validate_location(cls, v):
        """Validate location if provided."""
        if v is not None and not v.strip():
            return None  # Convert empty strings to None
        return v.strip() if v else v

    class Config:
        """Pydantic configuration."""
        str_strip_whitespace = True


class SiteCreate(SiteBase):
    """Model for creating a new site."""

    organization_id: uuid.UUID = Field(..., description="Parent organization ID")

    @validator('organization_id')
    def validate_organization_id(cls, v):
        """Validate organization ID format."""
        if not isinstance(v, uuid.UUID):
            try:
                uuid.UUID(str(v))
            except ValueError:
                raise ValueError('Invalid organization ID format')
        return v


class SiteUpdate(BaseModel):
    """Model for updating a site."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    location: Optional[str] = Field(None, max_length=255)
    timezone: Optional[str] = None

    @validator('slug')
    def validate_slug(cls, v):
        """Validate slug format if provided."""
        if v is not None:
            if not re.match(r'^[a-z0-9-]+$', v):
                raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
            if v.startswith('-') or v.endswith('-'):
                raise ValueError('Slug cannot start or end with a hyphen')
            if '--' in v:
                raise ValueError('Slug cannot contain consecutive hyphens')
        return v

    @validator('name')
    def validate_name(cls, v):
        """Validate site name if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError('Site name cannot be empty or whitespace only')
            return v.strip()
        return v

    @validator('timezone')
    def validate_timezone(cls, v):
        """Validate timezone if provided."""
        if v is not None:
            try:
                pytz.timezone(v)
            except pytz.exceptions.UnknownTimeZoneError:
                raise ValueError(f'Invalid timezone: {v}')
        return v

    @validator('location')
    def validate_location(cls, v):
        """Validate location if provided."""
        if v is not None and not v.strip():
            return None  # Convert empty strings to None
        return v.strip() if v else v

    class Config:
        """Pydantic configuration."""
        str_strip_whitespace = True


class Site(SiteBase):
    """Complete site model with all fields."""

    id: uuid.UUID = Field(..., description="Unique site identifier")
    organization_id: uuid.UUID = Field(..., description="Parent organization ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z',
            uuid.UUID: str
        }


class SiteWithStats(Site):
    """Site model with additional statistics."""

    area_count: int = Field(default=0, description="Number of areas in this site")
    device_count: int = Field(default=0, description="Total number of devices in this site")
    active_device_count: int = Field(default=0, description="Number of online devices")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class SiteList(BaseModel):
    """Model for site list responses."""

    sites: List[Site] = Field(default_factory=list)
    total: int = Field(default=0, description="Total number of sites")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


def generate_slug_from_name(name: str) -> str:
    """
    Generate a URL-safe slug from site name.

    Args:
        name: Site name

    Returns:
        URL-safe slug

    Example:
        generate_slug_from_name("Factory 01") -> "factory-01"
    """
    # Convert to lowercase
    slug = name.lower()

    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)

    # Remove non-alphanumeric characters except hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)

    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)

    # Remove leading and trailing hyphens
    slug = slug.strip('-')

    # Ensure minimum length
    if not slug:
        slug = f"site-{uuid.uuid4().hex[:8]}"

    return slug


def get_common_timezones() -> List[dict]:
    """
    Get list of common timezones for UI selection.

    Returns:
        List of timezone dictionaries with name and display label
    """
    common_timezones = [
        {"name": "UTC", "label": "UTC"},
        {"name": "US/Eastern", "label": "US Eastern"},
        {"name": "US/Central", "label": "US Central"},
        {"name": "US/Mountain", "label": "US Mountain"},
        {"name": "US/Pacific", "label": "US Pacific"},
        {"name": "Europe/London", "label": "London"},
        {"name": "Europe/Paris", "label": "Paris"},
        {"name": "Europe/Berlin", "label": "Berlin"},
        {"name": "Asia/Tokyo", "label": "Tokyo"},
        {"name": "Asia/Shanghai", "label": "Shanghai"},
        {"name": "Asia/Kolkata", "label": "India"},
        {"name": "Australia/Sydney", "label": "Sydney"},
    ]
    return common_timezones


def convert_timestamp_to_site_timezone(timestamp: datetime, site_timezone: str) -> datetime:
    """
    Convert UTC timestamp to site timezone.

    Args:
        timestamp: UTC timestamp
        site_timezone: Site timezone name

    Returns:
        Timestamp converted to site timezone
    """
    if timestamp.tzinfo is None:
        # Assume UTC if no timezone info
        timestamp = pytz.UTC.localize(timestamp)

    site_tz = pytz.timezone(site_timezone)
    return timestamp.astimezone(site_tz)


def validate_site_access(user_org_permissions: List[str], organization_id: str) -> bool:
    """
    Validate if user has permission to access site through organization.

    Args:
        user_org_permissions: List of organization IDs user has access to
        organization_id: Organization ID that owns the site

    Returns:
        True if user has access, False otherwise
    """
    return organization_id in user_org_permissions


class SiteRepository:
    """Repository pattern for site data access."""

    def __init__(self, db_session):
        """Initialize repository with database session."""
        self.db = db_session

    async def get_by_id(self, site_id: uuid.UUID) -> Optional[SiteTable]:
        """Get site by ID."""
        # Implementation would use actual database query
        pass

    async def get_by_organization_and_slug(self, org_id: uuid.UUID, slug: str) -> Optional[SiteTable]:
        """Get site by organization ID and slug."""
        # Implementation would use actual database query
        pass

    async def get_by_organization(self, org_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[SiteTable]:
        """Get all sites in an organization with pagination."""
        # Implementation would use actual database query
        pass

    async def create(self, site_data: SiteCreate) -> SiteTable:
        """Create new site."""
        # Implementation would use actual database query
        pass

    async def update(self, site_id: uuid.UUID, site_data: SiteUpdate) -> Optional[SiteTable]:
        """Update site."""
        # Implementation would use actual database query
        pass

    async def delete(self, site_id: uuid.UUID) -> bool:
        """Delete site."""
        # Implementation would use actual database query
        pass

    async def get_with_stats(self, site_id: uuid.UUID) -> Optional[dict]:
        """Get site with area/device statistics."""
        # Implementation would use actual database query with joins
        pass

    async def check_slug_exists_in_organization(self, org_id: uuid.UUID, slug: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
        """Check if slug already exists within organization."""
        # Implementation would use actual database query
        pass

    async def count_by_organization(self, org_id: uuid.UUID) -> int:
        """Count sites in organization."""
        # Implementation would use actual database query
        pass