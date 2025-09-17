"""
Authorization middleware for FastAPI application.

Provides role-based access control, organization-level permissions,
and request authorization for the IoT telemetry dashboard API.
"""

import logging
from typing import Optional, List, Callable, Dict, Any
from uuid import UUID
from functools import wraps

from fastapi import HTTPException, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..models.user import UserResponse, UserRole
from ..services.auth_service import get_auth_service, AuthService, get_current_user


logger = logging.getLogger(__name__)


class AuthorizationMiddleware:
    """Middleware for handling authorization and permissions."""

    def __init__(self, auth_service: AuthService):
        """
        Initialize authorization middleware.

        Args:
            auth_service: Authentication service
        """
        self.auth_service = auth_service

    async def check_organization_permission(
        self,
        user: UserResponse,
        organization_id: UUID
    ) -> bool:
        """
        Check if user has permission to access organization.

        Args:
            user: User to check permissions for
            organization_id: Organization UUID

        Returns:
            True if user has permission, False otherwise
        """
        return self.auth_service.check_permission(
            user=user,
            required_organization=organization_id
        )

    async def check_role_permission(
        self,
        user: UserResponse,
        required_role: UserRole
    ) -> bool:
        """
        Check if user has required role.

        Args:
            user: User to check permissions for
            required_role: Required minimum role

        Returns:
            True if user has permission, False otherwise
        """
        return self.auth_service.check_permission(
            user=user,
            required_role=required_role
        )

    async def validate_hierarchy_access(
        self,
        user: UserResponse,
        organization_id: Optional[UUID] = None,
        site_id: Optional[UUID] = None,
        area_id: Optional[UUID] = None,
        device_id: Optional[UUID] = None
    ) -> Dict[str, UUID]:
        """
        Validate user access to hierarchy elements and resolve IDs.

        Args:
            user: User to check permissions for
            organization_id: Optional organization UUID
            site_id: Optional site UUID
            area_id: Optional area UUID
            device_id: Optional device UUID

        Returns:
            Dictionary with resolved hierarchy IDs

        Raises:
            HTTPException: If access is denied or IDs are invalid
        """
        from ..services.postgresql_service import get_postgresql_service

        # Get database service
        try:
            db_service = await get_postgresql_service()
        except Exception as e:
            logger.error(f"Failed to get database service: {e}")
            raise HTTPException(
                status_code=500,
                detail="Database service not available"
            )

        resolved_ids = {}

        try:
            # If device_id is provided, resolve the full hierarchy
            if device_id:
                hierarchy_query = """
                    SELECT
                        d.id as device_id,
                        a.id as area_id,
                        s.id as site_id,
                        o.id as organization_id
                    FROM devices d
                    JOIN areas a ON d.area_id = a.id
                    JOIN sites s ON a.site_id = s.id
                    JOIN organizations o ON s.organization_id = o.id
                    WHERE d.id = $1
                """

                result = await db_service.execute_query_one(hierarchy_query, device_id)
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="Device not found"
                    )

                resolved_ids = {
                    'device_id': result['device_id'],
                    'area_id': result['area_id'],
                    'site_id': result['site_id'],
                    'organization_id': result['organization_id']
                }

            # If area_id is provided, resolve area hierarchy
            elif area_id:
                hierarchy_query = """
                    SELECT
                        a.id as area_id,
                        s.id as site_id,
                        o.id as organization_id
                    FROM areas a
                    JOIN sites s ON a.site_id = s.id
                    JOIN organizations o ON s.organization_id = o.id
                    WHERE a.id = $1
                """

                result = await db_service.execute_query_one(hierarchy_query, area_id)
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="Area not found"
                    )

                resolved_ids = {
                    'area_id': result['area_id'],
                    'site_id': result['site_id'],
                    'organization_id': result['organization_id']
                }

            # If site_id is provided, resolve site hierarchy
            elif site_id:
                hierarchy_query = """
                    SELECT
                        s.id as site_id,
                        o.id as organization_id
                    FROM sites s
                    JOIN organizations o ON s.organization_id = o.id
                    WHERE s.id = $1
                """

                result = await db_service.execute_query_one(hierarchy_query, site_id)
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="Site not found"
                    )

                resolved_ids = {
                    'site_id': result['site_id'],
                    'organization_id': result['organization_id']
                }

            # If only organization_id is provided
            elif organization_id:
                org_query = "SELECT id FROM organizations WHERE id = $1"
                result = await db_service.execute_query_one(org_query, organization_id)
                if not result:
                    raise HTTPException(
                        status_code=404,
                        detail="Organization not found"
                    )

                resolved_ids = {'organization_id': organization_id}

            # Check organization permission
            if 'organization_id' in resolved_ids:
                has_permission = await self.check_organization_permission(
                    user, resolved_ids['organization_id']
                )
                if not has_permission:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Insufficient permissions for organization"
                    )

            return resolved_ids

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating hierarchy access: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to validate access permissions"
            )


# Dependency functions for different permission levels
async def require_admin_role(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Dependency that requires admin role.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user if admin

    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    return current_user


async def require_operator_role(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Dependency that requires operator role or higher.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user if operator or admin

    Raises:
        HTTPException: If user doesn't have sufficient role
    """
    if current_user.role not in [UserRole.OPERATOR, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operator role or higher required"
        )
    return current_user


async def require_viewer_role(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    Dependency that requires viewer role or higher.

    Args:
        current_user: Current authenticated user

    Returns:
        Current user (all authenticated users are at least viewers)
    """
    return current_user


def require_organization_access(organization_param: str = "organization_id"):
    """
    Decorator factory for organization access validation.

    Args:
        organization_param: Parameter name containing organization ID

    Returns:
        Dependency function that validates organization access
    """
    async def validate_organization_access(
        request: Request,
        current_user: UserResponse = Depends(get_current_user),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> UserResponse:
        """Validate organization access."""
        try:
            # Get organization ID from path parameters
            organization_id_str = request.path_params.get(organization_param)
            if not organization_id_str:
                raise HTTPException(
                    status_code=400,
                    detail="Organization ID required"
                )

            organization_id = UUID(organization_id_str)

            # Check permission
            middleware = AuthorizationMiddleware(auth_service)
            has_permission = await middleware.check_organization_permission(
                current_user, organization_id
            )

            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions for organization"
                )

            return current_user

        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid organization ID format"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Organization access validation error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to validate organization access"
            )

    return validate_organization_access


def require_hierarchy_access():
    """
    Decorator for validating full hierarchy access.

    Returns:
        Dependency function that validates hierarchy access
    """
    async def validate_hierarchy_access(
        request: Request,
        current_user: UserResponse = Depends(get_current_user),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> Dict[str, Any]:
        """Validate hierarchy access and return resolved IDs."""
        try:
            # Extract hierarchy IDs from path parameters
            path_params = request.path_params

            organization_id = None
            site_id = None
            area_id = None
            device_id = None

            # Parse IDs from path parameters
            if "organization_id" in path_params:
                organization_id = UUID(path_params["organization_id"])
            if "site_id" in path_params:
                site_id = UUID(path_params["site_id"])
            if "area_id" in path_params:
                area_id = UUID(path_params["area_id"])
            if "device_id" in path_params:
                device_id = UUID(path_params["device_id"])

            # Validate access
            middleware = AuthorizationMiddleware(auth_service)
            resolved_ids = await middleware.validate_hierarchy_access(
                user=current_user,
                organization_id=organization_id,
                site_id=site_id,
                area_id=area_id,
                device_id=device_id
            )

            # Add user to result
            resolved_ids['current_user'] = current_user
            return resolved_ids

        except ValueError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ID format: {str(e)}"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Hierarchy access validation error: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to validate hierarchy access"
            )

    return validate_hierarchy_access


# Permission checker utility
class PermissionChecker:
    """Utility class for checking permissions."""

    @staticmethod
    def has_organization_access(user: UserResponse, organization_id: UUID) -> bool:
        """
        Check if user has access to organization.

        Args:
            user: User to check
            organization_id: Organization ID

        Returns:
            True if user has access
        """
        return (
            user.role == UserRole.ADMIN or
            organization_id in user.organization_permissions
        )

    @staticmethod
    def has_minimum_role(user: UserResponse, minimum_role: UserRole) -> bool:
        """
        Check if user has minimum required role.

        Args:
            user: User to check
            minimum_role: Minimum required role

        Returns:
            True if user has sufficient role
        """
        role_hierarchy = {
            UserRole.VIEWER: 1,
            UserRole.OPERATOR: 2,
            UserRole.ADMIN: 3
        }

        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(minimum_role, 999)

        return user_level >= required_level

    @staticmethod
    def can_modify_resource(user: UserResponse, organization_id: UUID) -> bool:
        """
        Check if user can modify resources in organization.

        Args:
            user: User to check
            organization_id: Organization ID

        Returns:
            True if user can modify resources
        """
        return (
            PermissionChecker.has_organization_access(user, organization_id) and
            PermissionChecker.has_minimum_role(user, UserRole.OPERATOR)
        )

    @staticmethod
    def can_delete_resource(user: UserResponse, organization_id: UUID) -> bool:
        """
        Check if user can delete resources in organization.

        Args:
            user: User to check
            organization_id: Organization ID

        Returns:
            True if user can delete resources
        """
        return (
            PermissionChecker.has_organization_access(user, organization_id) and
            user.role == UserRole.ADMIN
        )


# Global middleware instance
auth_middleware: Optional[AuthorizationMiddleware] = None


async def get_auth_middleware(
    auth_service: AuthService = Depends(get_auth_service)
) -> AuthorizationMiddleware:
    """
    Dependency function to get authorization middleware instance.

    Args:
        auth_service: Authentication service

    Returns:
        Authorization middleware instance
    """
    global auth_middleware

    if auth_middleware is None:
        auth_middleware = AuthorizationMiddleware(auth_service)

    return auth_middleware