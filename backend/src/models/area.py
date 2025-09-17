"""
Area model for IoT Telemetry Dashboard.

Represents the third level in the organizational hierarchy:
Organization -> Sites -> Areas -> Devices

This model handles area metadata, descriptions,
and relationships with sites and devices.
"""

from datetime import datetime
from typing import List, Optional
import uuid
import re

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from .site import SiteTable


Base = declarative_base()


class AreaTable(Base):
    """SQLAlchemy table definition for areas."""

    __tablename__ = "areas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id = Column(UUID(as_uuid=True), ForeignKey("sites.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    site = relationship("SiteTable", back_populates="areas")
    devices = relationship("DeviceTable", back_populates="area", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Area(id={self.id}, name='{self.name}', slug='{self.slug}', site_id={self.site_id})>"


class AreaBase(BaseModel):
    """Base area model with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Area name")
    slug: str = Field(..., min_length=1, max_length=255, description="URL-safe area identifier within site")
    description: Optional[str] = Field(None, description="Optional area description")

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
        """Validate area name."""
        if not v.strip():
            raise ValueError('Area name cannot be empty or whitespace only')
        return v.strip()

    @validator('description')
    def validate_description(cls, v):
        """Validate description if provided."""
        if v is not None and not v.strip():
            return None  # Convert empty strings to None
        return v.strip() if v else v

    class Config:
        """Pydantic configuration."""
        str_strip_whitespace = True


class AreaCreate(AreaBase):
    """Model for creating a new area."""

    site_id: uuid.UUID = Field(..., description="Parent site ID")

    @validator('site_id')
    def validate_site_id(cls, v):
        """Validate site ID format."""
        if not isinstance(v, uuid.UUID):
            try:
                uuid.UUID(str(v))
            except ValueError:
                raise ValueError('Invalid site ID format')
        return v


class AreaUpdate(BaseModel):
    """Model for updating an area."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    slug: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None

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
        """Validate area name if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError('Area name cannot be empty or whitespace only')
            return v.strip()
        return v

    @validator('description')
    def validate_description(cls, v):
        """Validate description if provided."""
        if v is not None and not v.strip():
            return None  # Convert empty strings to None
        return v.strip() if v else v

    class Config:
        """Pydantic configuration."""
        str_strip_whitespace = True


class Area(AreaBase):
    """Complete area model with all fields."""

    id: uuid.UUID = Field(..., description="Unique area identifier")
    site_id: uuid.UUID = Field(..., description="Parent site ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z',
            uuid.UUID: str
        }


class AreaWithStats(Area):
    """Area model with additional statistics."""

    device_count: int = Field(default=0, description="Number of devices in this area")
    active_device_count: int = Field(default=0, description="Number of online devices")
    offline_device_count: int = Field(default=0, description="Number of offline devices")
    maintenance_device_count: int = Field(default=0, description="Number of devices in maintenance")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class AreaWithHierarchy(Area):
    """Area model with full hierarchy context."""

    organization_name: str = Field(..., description="Organization name")
    organization_slug: str = Field(..., description="Organization slug")
    site_name: str = Field(..., description="Site name")
    site_slug: str = Field(..., description="Site slug")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class AreaList(BaseModel):
    """Model for area list responses."""

    areas: List[Area] = Field(default_factory=list)
    total: int = Field(default=0, description="Total number of areas")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


def generate_slug_from_name(name: str) -> str:
    """
    Generate a URL-safe slug from area name.

    Args:
        name: Area name

    Returns:
        URL-safe slug

    Example:
        generate_slug_from_name("Production Floor") -> "production-floor"
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
        slug = f"area-{uuid.uuid4().hex[:8]}"

    return slug


def get_area_types() -> List[dict]:
    """
    Get list of common area types for UI selection.

    Returns:
        List of area type dictionaries with name and description
    """
    area_types = [
        {"name": "production", "label": "Production Floor", "description": "Manufacturing and production areas"},
        {"name": "warehouse", "label": "Warehouse", "description": "Storage and inventory areas"},
        {"name": "office", "label": "Office", "description": "Administrative and office spaces"},
        {"name": "maintenance", "label": "Maintenance", "description": "Equipment maintenance areas"},
        {"name": "laboratory", "label": "Laboratory", "description": "Testing and quality control labs"},
        {"name": "shipping", "label": "Shipping & Receiving", "description": "Logistics and shipping areas"},
        {"name": "utilities", "label": "Utilities", "description": "Power, HVAC, and utility systems"},
        {"name": "outdoor", "label": "Outdoor", "description": "External and outdoor monitoring areas"},
        {"name": "server-room", "label": "Server Room", "description": "IT infrastructure and data centers"},
        {"name": "break-room", "label": "Break Room", "description": "Employee common areas"},
        {"name": "other", "label": "Other", "description": "Other specialized areas"}
    ]
    return area_types


def validate_area_access(user_org_permissions: List[str], organization_id: str) -> bool:
    """
    Validate if user has permission to access area through organization.

    Args:
        user_org_permissions: List of organization IDs user has access to
        organization_id: Organization ID that owns the area's site

    Returns:
        True if user has access, False otherwise
    """
    return organization_id in user_org_permissions


def build_area_hierarchy_path(organization_slug: str, site_slug: str, area_slug: str) -> str:
    """
    Build hierarchical path for area.

    Args:
        organization_slug: Organization slug
        site_slug: Site slug
        area_slug: Area slug

    Returns:
        Hierarchical path string

    Example:
        build_area_hierarchy_path("acme-corp", "factory-01", "production-floor")
        -> "acme-corp/factory-01/production-floor"
    """
    return f"{organization_slug}/{site_slug}/{area_slug}"


class AreaRepository:
    """Repository pattern for area data access."""

    def __init__(self, db_session):
        """Initialize repository with database session."""
        self.db = db_session

    async def get_by_id(self, area_id: uuid.UUID) -> Optional[AreaTable]:
        """Get area by ID."""
        # Implementation would use actual database query
        pass

    async def get_by_site_and_slug(self, site_id: uuid.UUID, slug: str) -> Optional[AreaTable]:
        """Get area by site ID and slug."""
        # Implementation would use actual database query
        pass

    async def get_by_site(self, site_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[AreaTable]:
        """Get all areas in a site with pagination."""
        # Implementation would use actual database query
        pass

    async def get_by_organization(self, org_id: uuid.UUID, skip: int = 0, limit: int = 100) -> List[AreaTable]:
        """Get all areas in an organization with pagination."""
        # Implementation would use actual database query with joins
        pass

    async def create(self, area_data: AreaCreate) -> AreaTable:
        """Create new area."""
        # Implementation would use actual database query
        pass

    async def update(self, area_id: uuid.UUID, area_data: AreaUpdate) -> Optional[AreaTable]:
        """Update area."""
        # Implementation would use actual database query
        pass

    async def delete(self, area_id: uuid.UUID) -> bool:
        """Delete area."""
        # Implementation would use actual database query
        pass

    async def get_with_stats(self, area_id: uuid.UUID) -> Optional[dict]:
        """Get area with device statistics."""
        # Implementation would use actual database query with joins
        pass

    async def get_with_hierarchy(self, area_id: uuid.UUID) -> Optional[dict]:
        """Get area with full hierarchy context."""
        # Implementation would use actual database query with joins
        pass

    async def check_slug_exists_in_site(self, site_id: uuid.UUID, slug: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
        """Check if slug already exists within site."""
        # Implementation would use actual database query
        pass

    async def count_by_site(self, site_id: uuid.UUID) -> int:
        """Count areas in site."""
        # Implementation would use actual database query
        pass

    async def count_by_organization(self, org_id: uuid.UUID) -> int:
        """Count areas in organization."""
        # Implementation would use actual database query with joins
        pass

    async def search_by_name(self, search_term: str, org_id: Optional[uuid.UUID] = None, limit: int = 50) -> List[AreaTable]:
        """Search areas by name."""
        # Implementation would use actual database query with text search
        pass