"""
User model for IoT Telemetry Dashboard.

Handles user authentication, authorization, and organization permissions.
Supports role-based access control with admin, operator, and viewer roles.
"""

from datetime import datetime
from typing import List, Optional, Literal
from enum import Enum
import uuid
import re

from pydantic import BaseModel, Field, validator, EmailStr
from sqlalchemy import Column, String, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from passlib.context import CryptContext


Base = declarative_base()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, Enum):
    """User role enumeration."""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class UserTable(Base):
    """SQLAlchemy table definition for users."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.VIEWER, index=True)
    organization_permissions = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=[])
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', name='{self.name}', role={self.role})>"


class UserBase(BaseModel):
    """Base user model with common fields."""

    email: EmailStr = Field(..., description="User email address")
    name: str = Field(..., min_length=1, max_length=255, description="User full name")
    role: UserRole = Field(default=UserRole.VIEWER, description="User role")
    organization_permissions: List[uuid.UUID] = Field(default_factory=list, description="Organization IDs user has access to")

    @validator('name')
    def validate_name(cls, v):
        """Validate user name."""
        if not v.strip():
            raise ValueError('User name cannot be empty or whitespace only')
        return v.strip()

    @validator('organization_permissions')
    def validate_organization_permissions(cls, v):
        """Validate organization permissions."""
        if not isinstance(v, list):
            raise ValueError('Organization permissions must be a list')

        # Validate each UUID
        for org_id in v:
            if not isinstance(org_id, uuid.UUID):
                try:
                    uuid.UUID(str(org_id))
                except ValueError:
                    raise ValueError(f'Invalid organization ID format: {org_id}')

        # Remove duplicates while preserving order
        seen = set()
        unique_perms = []
        for org_id in v:
            if org_id not in seen:
                seen.add(org_id)
                unique_perms.append(org_id)

        return unique_perms

    class Config:
        """Pydantic configuration."""
        str_strip_whitespace = True


class UserCreate(UserBase):
    """Model for creating a new user."""

    password: str = Field(..., min_length=8, description="User password")

    @validator('password')
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        # Check for at least one uppercase, one lowercase, and one digit
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')

        return v

    class Config:
        """Pydantic configuration."""
        str_strip_whitespace = True


class UserUpdate(BaseModel):
    """Model for updating a user."""

    email: Optional[EmailStr] = None
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[UserRole] = None
    organization_permissions: Optional[List[uuid.UUID]] = None

    @validator('name')
    def validate_name(cls, v):
        """Validate user name if provided."""
        if v is not None:
            if not v.strip():
                raise ValueError('User name cannot be empty or whitespace only')
            return v.strip()
        return v

    @validator('organization_permissions')
    def validate_organization_permissions(cls, v):
        """Validate organization permissions if provided."""
        if v is not None:
            if not isinstance(v, list):
                raise ValueError('Organization permissions must be a list')

            # Validate each UUID
            for org_id in v:
                if not isinstance(org_id, uuid.UUID):
                    try:
                        uuid.UUID(str(org_id))
                    except ValueError:
                        raise ValueError(f'Invalid organization ID format: {org_id}')

            # Remove duplicates while preserving order
            seen = set()
            unique_perms = []
            for org_id in v:
                if org_id not in seen:
                    seen.add(org_id)
                    unique_perms.append(org_id)

            return unique_perms
        return v

    class Config:
        """Pydantic configuration."""
        str_strip_whitespace = True


class UserPasswordUpdate(BaseModel):
    """Model for updating user password."""

    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password")

    @validator('new_password')
    def validate_new_password(cls, v):
        """Validate new password strength."""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')

        # Check for at least one uppercase, one lowercase, and one digit
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')

        return v


class User(UserBase):
    """Complete user model with all fields (excluding password)."""

    id: uuid.UUID = Field(..., description="Unique user identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        """Pydantic configuration."""
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + 'Z',
            uuid.UUID: str
        }


class UserWithPermissionDetails(User):
    """User model with detailed permission information."""

    accessible_organizations: List[dict] = Field(default_factory=list, description="Organizations user can access with details")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class UserList(BaseModel):
    """Model for user list responses."""

    users: List[User] = Field(default_factory=list)
    total: int = Field(default=0, description="Total number of users")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


class UserLogin(BaseModel):
    """Model for user login."""

    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UserLoginResponse(BaseModel):
    """Model for login response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user: User = Field(..., description="User information")

    class Config:
        """Pydantic configuration."""
        from_attributes = True


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_role_permissions(role: UserRole) -> dict:
    """
    Get permissions for a user role.

    Args:
        role: User role

    Returns:
        Dictionary of permissions
    """
    permissions = {
        UserRole.ADMIN: {
            "can_create_organizations": True,
            "can_manage_users": True,
            "can_manage_devices": True,
            "can_view_all_data": True,
            "can_modify_system_settings": True,
            "can_delete_data": True
        },
        UserRole.OPERATOR: {
            "can_create_organizations": False,
            "can_manage_users": False,
            "can_manage_devices": True,
            "can_view_all_data": True,
            "can_modify_system_settings": False,
            "can_delete_data": False
        },
        UserRole.VIEWER: {
            "can_create_organizations": False,
            "can_manage_users": False,
            "can_manage_devices": False,
            "can_view_all_data": True,
            "can_modify_system_settings": False,
            "can_delete_data": False
        }
    }
    return permissions.get(role, permissions[UserRole.VIEWER])


def validate_user_organization_access(user: User, organization_id: uuid.UUID) -> bool:
    """
    Validate if user has access to a specific organization.

    Args:
        user: User object
        organization_id: Organization ID to check

    Returns:
        True if user has access, False otherwise
    """
    # Admins have access to all organizations
    if user.role == UserRole.ADMIN:
        return True

    # Check if organization is in user's permissions
    return organization_id in user.organization_permissions


def can_user_manage_organization(user: User, organization_id: uuid.UUID) -> bool:
    """
    Check if user can manage (create/update/delete) resources in an organization.

    Args:
        user: User object
        organization_id: Organization ID

    Returns:
        True if user can manage organization, False otherwise
    """
    # Only admins and operators can manage resources
    if user.role not in [UserRole.ADMIN, UserRole.OPERATOR]:
        return False

    return validate_user_organization_access(user, organization_id)


def get_user_accessible_organization_ids(user: User) -> List[uuid.UUID]:
    """
    Get list of organization IDs that user can access.

    Args:
        user: User object

    Returns:
        List of accessible organization IDs
    """
    # Admins have access to all organizations (this would need special handling in queries)
    if user.role == UserRole.ADMIN:
        return []  # Empty list indicates "all organizations"

    return user.organization_permissions


class UserRepository:
    """Repository pattern for user data access."""

    def __init__(self, db_session):
        """Initialize repository with database session."""
        self.db = db_session

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[UserTable]:
        """Get user by ID."""
        # Implementation would use actual database query
        pass

    async def get_by_email(self, email: str) -> Optional[UserTable]:
        """Get user by email."""
        # Implementation would use actual database query
        pass

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[UserTable]:
        """Get all users with pagination."""
        # Implementation would use actual database query
        pass

    async def create(self, user_data: UserCreate) -> UserTable:
        """Create new user."""
        # Implementation would use actual database query
        # Remember to hash password before storing
        pass

    async def update(self, user_id: uuid.UUID, user_data: UserUpdate) -> Optional[UserTable]:
        """Update user."""
        # Implementation would use actual database query
        pass

    async def update_password(self, user_id: uuid.UUID, password_data: UserPasswordUpdate) -> bool:
        """Update user password."""
        # Implementation would use actual database query
        # Remember to verify current password and hash new password
        pass

    async def delete(self, user_id: uuid.UUID) -> bool:
        """Delete user."""
        # Implementation would use actual database query
        pass

    async def authenticate(self, email: str, password: str) -> Optional[UserTable]:
        """Authenticate user by email and password."""
        # Implementation would use actual database query
        # Remember to verify password hash
        pass

    async def get_by_organization(self, org_id: uuid.UUID) -> List[UserTable]:
        """Get users who have access to a specific organization."""
        # Implementation would use actual database query
        pass

    async def add_organization_permission(self, user_id: uuid.UUID, org_id: uuid.UUID) -> bool:
        """Add organization permission to user."""
        # Implementation would use actual database query
        pass

    async def remove_organization_permission(self, user_id: uuid.UUID, org_id: uuid.UUID) -> bool:
        """Remove organization permission from user."""
        # Implementation would use actual database query
        pass

    async def check_email_exists(self, email: str, exclude_id: Optional[uuid.UUID] = None) -> bool:
        """Check if email already exists."""
        # Implementation would use actual database query
        pass

    async def count_by_role(self, role: UserRole) -> int:
        """Count users by role."""
        # Implementation would use actual database query
        pass