"""
Organization model for IoT Telemetry Dashboard.

Represents the top-level organizational entity in the hierarchy:
Organization -> Sites -> Areas -> Devices

This model handles organization metadata, slug validation,
and relationships with sites and users.
"""

from datetime import datetime
from typing import List, Optional
import uuid
import re

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class OrganizationTable(Base):
    """SQLAlchemy table definition for organizations."""

    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sites = relationship("SiteTable", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization(id={self.id}, name='{self.name}', slug='{self.slug}')>"


class OrganizationBase(BaseModel):
    """Base organization model with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Organization name")
    slug: str = Field(..., min_length=1, max_length=255, description="URL-safe organization identifier")
    description: Optional[str] = Field(None, description="Optional organization description")

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
        """Validate organization name."""
        if not v.strip():
            raise ValueError('Organization name cannot be empty or whitespace only')
        return v.strip()

    class Config:
        """Pydantic configuration."""
        str_strip_whitespace = True


class OrganizationCreate(OrganizationBase):
    """Model for creating a new organization."""
    pass


class OrganizationUpdate(BaseModel):
    """Model for updating an organization."""

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
        """Validate organization name if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError('Organization name cannot be empty or whitespace only')
            return v.strip()
        return v

    class Config:
        """Pydantic configuration."""
        str_strip_whitespace = True


class Organization(OrganizationBase):
    """Complete organization model with all fields."""

    id: uuid.UUID = Field(..., description="Unique organization identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z',
            uuid.UUID: str
        }


class OrganizationWithStats(Organization):
    """Organization model with additional statistics."""

    site_count: int = Field(default=0, description="Number of sites in this organization")
    device_count: int = Field(default=0, description="Total number of devices in this organization")
    active_device_count: int = Field(default=0, description="Number of online devices")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class OrganizationList(BaseModel):
    """Model for organization list responses."""

    organizations: List[Organization] = Field(default_factory=list)
    total: int = Field(default=0, description="Total number of organizations")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


def generate_slug_from_name(name: str) -> str:
    """
    Generate a URL-safe slug from organization name.

    Args:
        name: Organization name

    Returns:
        URL-safe slug

    Example:
        generate_slug_from_name("ACME Corporation") -> "acme-corporation"
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
        slug = f"org-{uuid.uuid4().hex[:8]}"

    return slug


def validate_organization_permissions(user_org_permissions: List[str], org_id: str) -> bool:
    """
    Validate if user has permission to access organization.

    Args:
        user_org_permissions: List of organization IDs user has access to
        org_id: Organization ID to check access for

    Returns:
        True if user has access, False otherwise
    """
    return org_id in user_org_permissions


class OrganizationRepository:
    """Repository pattern for organization data access."""

    def __init__(self, db_session):
        """Initialize repository with database session."""
        self.db = db_session

    async def get_by_id(self, org_id: uuid.UUID) -> Optional[OrganizationTable]:
        """Get organization by ID."""
        # Implementation would use actual database query
        # For now, this is a placeholder for the interface
        pass

    async def get_by_slug(self, slug: str) -> Optional[OrganizationTable]:
        """Get organization by slug."""
        # Implementation would use actual database query
        pass

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[OrganizationTable]:
        """Get all organizations with pagination."""
        # Implementation would use actual database query
        pass

    async def create(self, org_data: OrganizationCreate) -> OrganizationTable:
        """Create new organization."""
        # Implementation would use actual database query
        pass

    async def update(self, org_id: uuid.UUID, org_data: OrganizationUpdate) -> Optional[OrganizationTable]:
        """Update organization."""
        # Implementation would use actual database query
        pass

    async def delete(self, org_id: uuid.UUID) -> bool:
        """Delete organization."""
        # Implementation would use actual database query
        pass

    async def get_with_stats(self, org_id: uuid.UUID) -> Optional[dict]:
        """Get organization with site/device statistics."""
        # Implementation would use actual database query with joins
        pass

    async def check_slug_exists(self, slug: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
        """Check if slug already exists."""
        # Implementation would use actual database query
        pass