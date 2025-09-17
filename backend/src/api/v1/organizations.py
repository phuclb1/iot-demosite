"""
Organizations API endpoints.

Provides REST API endpoints for organization management including
listing, creation, updating, and deletion of organizations.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from ...models.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from ...models.user import UserResponse
from ...services.organization_service import get_organization_service, OrganizationService
from ...middleware.auth_middleware import (
    require_viewer_role,
    require_operator_role,
    require_admin_role,
    require_organization_access
)


logger = logging.getLogger(__name__)

# Create router for organizations
router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.get(
    "",
    response_model=List[OrganizationResponse],
    summary="List organizations",
    description="Get list of organizations with pagination. Users see only organizations they have access to."
)
async def list_organizations(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search query for organization name or description"),
    current_user: UserResponse = Depends(require_viewer_role),
    org_service: OrganizationService = Depends(get_organization_service)
) -> List[OrganizationResponse]:
    """
    List organizations with pagination and optional search.

    Users will only see organizations they have permission to access.
    Admins see all organizations, other users see only their assigned organizations.
    """
    try:
        if search:
            # Search organizations
            organizations = await org_service.search_organizations(
                query=search,
                skip=skip,
                limit=limit
            )
        else:
            # List all organizations
            organizations = await org_service.list_organizations(
                skip=skip,
                limit=limit
            )

        # Filter organizations based on user permissions
        if current_user.role.value != "admin":
            # Non-admin users only see organizations they have access to
            accessible_orgs = []
            for org in organizations:
                if org.id in current_user.organization_permissions:
                    accessible_orgs.append(org)
            organizations = accessible_orgs

        logger.info(f"Listed {len(organizations)} organizations for user {current_user.email}")
        return organizations

    except Exception as e:
        logger.error(f"Error listing organizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list organizations"
        )


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
    summary="Get organization",
    description="Get organization details by ID. Requires permission to access the organization."
)
async def get_organization(
    organization_id: UUID,
    current_user: UserResponse = Depends(require_organization_access()),
    org_service: OrganizationService = Depends(get_organization_service)
) -> OrganizationResponse:
    """
    Get organization details by ID.

    User must have permission to access the organization.
    """
    try:
        organization = await org_service.get_organization(organization_id)

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        logger.info(f"Retrieved organization {organization_id} for user {current_user.email}")
        return organization

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization"
        )


@router.get(
    "/{organization_id}/stats",
    summary="Get organization statistics",
    description="Get organization statistics including site, area, and device counts."
)
async def get_organization_stats(
    organization_id: UUID,
    current_user: UserResponse = Depends(require_organization_access()),
    org_service: OrganizationService = Depends(get_organization_service)
):
    """
    Get organization statistics.

    Returns counts of sites, areas, devices, and device status distribution.
    """
    try:
        stats = await org_service.get_organization_stats(organization_id)

        logger.info(f"Retrieved stats for organization {organization_id}")
        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization stats {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization statistics"
        )


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create organization",
    description="Create a new organization. Requires admin role."
)
async def create_organization(
    organization_data: OrganizationCreate,
    current_user: UserResponse = Depends(require_admin_role),
    org_service: OrganizationService = Depends(get_organization_service)
) -> OrganizationResponse:
    """
    Create a new organization.

    Only admin users can create organizations.
    """
    try:
        organization = await org_service.create_organization(organization_data)

        logger.info(f"Created organization {organization.id} by user {current_user.email}")
        return organization

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating organization: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create organization"
        )


@router.put(
    "/{organization_id}",
    response_model=OrganizationResponse,
    summary="Update organization",
    description="Update organization details. Requires admin role."
)
async def update_organization(
    organization_id: UUID,
    organization_data: OrganizationUpdate,
    current_user: UserResponse = Depends(require_admin_role),
    org_service: OrganizationService = Depends(get_organization_service)
) -> OrganizationResponse:
    """
    Update organization details.

    Only admin users can update organizations.
    """
    try:
        organization = await org_service.update_organization(organization_id, organization_data)

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        logger.info(f"Updated organization {organization_id} by user {current_user.email}")
        return organization

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating organization {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update organization"
        )


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete organization",
    description="Delete organization and all its associated data. Requires admin role."
)
async def delete_organization(
    organization_id: UUID,
    current_user: UserResponse = Depends(require_admin_role),
    org_service: OrganizationService = Depends(get_organization_service)
):
    """
    Delete organization and all its associated data.

    Only admin users can delete organizations.
    This will cascade delete all sites, areas, and devices within the organization.
    """
    try:
        deleted = await org_service.delete_organization(organization_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        logger.info(f"Deleted organization {organization_id} by user {current_user.email}")
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting organization {organization_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete organization"
        )


@router.get(
    "/{organization_id}/slug/{slug}",
    response_model=OrganizationResponse,
    summary="Get organization by slug",
    description="Get organization details by slug. For internal use or direct access."
)
async def get_organization_by_slug(
    organization_id: UUID,
    slug: str,
    current_user: UserResponse = Depends(require_organization_access()),
    org_service: OrganizationService = Depends(get_organization_service)
) -> OrganizationResponse:
    """
    Get organization by slug.

    This endpoint is primarily for validation or direct slug-based access.
    """
    try:
        organization = await org_service.get_organization_by_slug(slug)

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        # Verify the organization_id matches
        if organization.id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization ID and slug do not match"
            )

        logger.info(f"Retrieved organization by slug {slug}")
        return organization

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization by slug {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve organization"
        )