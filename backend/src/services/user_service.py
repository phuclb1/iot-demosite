"""
User service for CRUD operations and authentication.

Provides business logic layer for user management including
creation, retrieval, updating, deletion, and password management.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import HTTPException, Depends

from ..models.user import (
    UserTable,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserRepository,
    UserRole
)
from ..services.postgresql_service import get_postgresql_service, PostgreSQLService


logger = logging.getLogger(__name__)


class UserService:
    """Service class for user operations."""

    def __init__(self, db_service: PostgreSQLService):
        """
        Initialize user service.

        Args:
            db_service: PostgreSQL database service
        """
        self.db_service = db_service
        self.repository = UserRepository()

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """
        Create a new user.

        Args:
            user_data: User creation data

        Returns:
            Created user

        Raises:
            HTTPException: If creation fails or email already exists
        """
        try:
            # Check if email already exists
            existing = await self.get_user_by_email(user_data.email)
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"User with email '{user_data.email}' already exists"
                )

            # Validate organization permissions if provided
            if user_data.organization_permissions:
                await self._validate_organization_permissions(user_data.organization_permissions)

            # Create user using repository
            async with self.db_service.get_connection() as conn:
                user = await self.repository.create(conn, user_data)

            logger.info(f"Created user: {user.id} ({user.email})")
            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create user"
            )

    async def get_user(self, user_id: UUID) -> Optional[UserResponse]:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User if found, None otherwise

        Raises:
            HTTPException: If database operation fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                user = await self.repository.get_by_id(conn, user_id)

            if user:
                logger.debug(f"Retrieved user: {user_id}")

            return user

        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve user"
            )

    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """
        Get user by email address.

        Args:
            email: User email address

        Returns:
            User if found, None otherwise

        Raises:
            HTTPException: If database operation fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                user = await self.repository.get_by_email(conn, email)

            if user:
                logger.debug(f"Retrieved user by email: {email}")

            return user

        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve user"
            )

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role_filter: Optional[UserRole] = None
    ) -> List[UserResponse]:
        """
        List users with pagination and optional role filter.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            role_filter: Optional user role filter

        Returns:
            List of users

        Raises:
            HTTPException: If database operation fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                users = await self.repository.list(conn, skip, limit, role_filter)

            logger.debug(f"Listed {len(users)} users")
            return users

        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to list users"
            )

    async def update_user(
        self,
        user_id: UUID,
        user_data: UserUpdate
    ) -> Optional[UserResponse]:
        """
        Update user.

        Args:
            user_id: User UUID
            user_data: User update data

        Returns:
            Updated user if found, None otherwise

        Raises:
            HTTPException: If update fails or email conflicts
        """
        try:
            # Check if user exists
            existing = await self.get_user(user_id)
            if not existing:
                return None

            # Check email uniqueness if changing
            if user_data.email and user_data.email != existing.email:
                email_exists = await self.get_user_by_email(user_data.email)
                if email_exists:
                    raise HTTPException(
                        status_code=400,
                        detail=f"User with email '{user_data.email}' already exists"
                    )

            # Validate organization permissions if provided
            if user_data.organization_permissions is not None:
                await self._validate_organization_permissions(user_data.organization_permissions)

            # Update user using repository
            async with self.db_service.get_connection() as conn:
                user = await self.repository.update(conn, user_id, user_data)

            if user:
                logger.info(f"Updated user: {user_id}")

            return user

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update user {user_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to update user"
            )

    async def delete_user(self, user_id: UUID) -> bool:
        """
        Delete user.

        Args:
            user_id: User UUID

        Returns:
            True if deleted, False if not found

        Raises:
            HTTPException: If deletion fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                deleted = await self.repository.delete(conn, user_id)

            if deleted:
                logger.info(f"Deleted user: {user_id}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete user {user_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to delete user"
            )

    async def verify_password(self, user_id: UUID, password: str) -> bool:
        """
        Verify user password.

        Args:
            user_id: User UUID
            password: Plain text password to verify

        Returns:
            True if password is correct, False otherwise

        Raises:
            HTTPException: If verification fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                return await self.repository.verify_password(conn, user_id, password)

        except Exception as e:
            logger.error(f"Failed to verify password for user {user_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to verify password"
            )

    async def change_password(self, user_id: UUID, new_password: str) -> bool:
        """
        Change user password.

        Args:
            user_id: User UUID
            new_password: New plain text password

        Returns:
            True if password was changed, False if user not found

        Raises:
            HTTPException: If password change fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                success = await self.repository.change_password(conn, user_id, new_password)

            if success:
                logger.info(f"Changed password for user: {user_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to change password for user {user_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to change password"
            )

    async def search_users(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserResponse]:
        """
        Search users by name or email.

        Args:
            query: Search query string
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching users

        Raises:
            HTTPException: If search fails
        """
        try:
            search_query = """
                SELECT id, email, name, role, organization_permissions, created_at, updated_at
                FROM users
                WHERE
                    name ILIKE $1 OR
                    email ILIKE $1
                ORDER BY name
                OFFSET $2 LIMIT $3
            """

            search_pattern = f"%{query}%"
            results = await self.db_service.execute_query(
                search_query, search_pattern, skip, limit
            )

            users = [
                UserResponse(**dict(row)) for row in results
            ]

            logger.debug(f"Found {len(users)} users matching '{query}'")
            return users

        except Exception as e:
            logger.error(f"Failed to search users with query '{query}': {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to search users"
            )

    async def get_users_by_organization(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[UserResponse]:
        """
        Get users who have access to a specific organization.

        Args:
            organization_id: Organization UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of users with access to the organization

        Raises:
            HTTPException: If operation fails
        """
        try:
            # Verify organization exists
            org_check_query = "SELECT id FROM organizations WHERE id = $1"
            org_exists = await self.db_service.execute_query_one(org_check_query, organization_id)
            if not org_exists:
                raise HTTPException(
                    status_code=404,
                    detail="Organization not found"
                )

            org_users_query = """
                SELECT id, email, name, role, organization_permissions, created_at, updated_at
                FROM users
                WHERE
                    role = 'admin' OR
                    $1 = ANY(organization_permissions)
                ORDER BY name
                OFFSET $2 LIMIT $3
            """

            results = await self.db_service.execute_query(
                org_users_query, organization_id, skip, limit
            )

            users = [
                UserResponse(**dict(row)) for row in results
            ]

            logger.debug(f"Found {len(users)} users for organization {organization_id}")
            return users

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get users for organization {organization_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to get users for organization"
            )

    async def grant_organization_access(
        self,
        user_id: UUID,
        organization_id: UUID
    ) -> bool:
        """
        Grant user access to an organization.

        Args:
            user_id: User UUID
            organization_id: Organization UUID

        Returns:
            True if access was granted, False if user not found

        Raises:
            HTTPException: If operation fails
        """
        try:
            # Verify organization exists
            org_check_query = "SELECT id FROM organizations WHERE id = $1"
            org_exists = await self.db_service.execute_query_one(org_check_query, organization_id)
            if not org_exists:
                raise HTTPException(
                    status_code=404,
                    detail="Organization not found"
                )

            # Get current user
            user = await self.get_user(user_id)
            if not user:
                return False

            # Check if user already has access
            if organization_id in user.organization_permissions:
                return True

            # Add organization to permissions
            new_permissions = list(user.organization_permissions) + [organization_id]
            update_data = UserUpdate(organization_permissions=new_permissions)

            updated_user = await self.update_user(user_id, update_data)
            success = updated_user is not None

            if success:
                logger.info(f"Granted organization {organization_id} access to user {user_id}")

            return success

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to grant organization access: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to grant organization access"
            )

    async def revoke_organization_access(
        self,
        user_id: UUID,
        organization_id: UUID
    ) -> bool:
        """
        Revoke user access from an organization.

        Args:
            user_id: User UUID
            organization_id: Organization UUID

        Returns:
            True if access was revoked, False if user not found

        Raises:
            HTTPException: If operation fails
        """
        try:
            # Get current user
            user = await self.get_user(user_id)
            if not user:
                return False

            # Check if user has access
            if organization_id not in user.organization_permissions:
                return True

            # Remove organization from permissions
            new_permissions = [
                org_id for org_id in user.organization_permissions
                if org_id != organization_id
            ]
            update_data = UserUpdate(organization_permissions=new_permissions)

            updated_user = await self.update_user(user_id, update_data)
            success = updated_user is not None

            if success:
                logger.info(f"Revoked organization {organization_id} access from user {user_id}")

            return success

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to revoke organization access: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to revoke organization access"
            )

    async def _validate_organization_permissions(self, organization_ids: List[UUID]) -> None:
        """
        Validate that all organization IDs exist.

        Args:
            organization_ids: List of organization UUIDs to validate

        Raises:
            HTTPException: If any organization doesn't exist
        """
        if not organization_ids:
            return

        for org_id in organization_ids:
            org_check_query = "SELECT id FROM organizations WHERE id = $1"
            org_exists = await self.db_service.execute_query_one(org_check_query, org_id)
            if not org_exists:
                raise HTTPException(
                    status_code=400,
                    detail=f"Organization {org_id} does not exist"
                )


async def get_user_service(
    db_service: PostgreSQLService = Depends(get_postgresql_service)
) -> UserService:
    """
    Dependency function to get user service.

    Args:
        db_service: PostgreSQL database service

    Returns:
        User service instance
    """
    return UserService(db_service)