"""
Sites API endpoints.

Provides REST API endpoints for site management within organizations
including listing, creation, updating, and deletion of sites.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from ...models.site import SiteCreate, SiteUpdate, SiteResponse
from ...models.user import UserResponse
from ...services.site_service import get_site_service, SiteService
from ...middleware.auth_middleware import (
    require_viewer_role,
    require_operator_role,
    require_admin_role,
    require_hierarchy_access
)


logger = logging.getLogger(__name__)

# Create router for sites
router = APIRouter(prefix="/organizations/{organization_id}/sites", tags=["sites"])


@router.get(
    "",
    response_model=List[SiteResponse],
    summary="List sites in organization",
    description="Get list of sites within an organization with pagination."
)
async def list_sites(
    organization_id: UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search query for site name or location"),
    timezone: Optional[str] = Query(None, description="Filter by timezone"),
    current_user: UserResponse = Depends(require_viewer_role),
    site_service: SiteService = Depends(get_site_service)
) -> List[SiteResponse]:
    """
    List sites within an organization.

    Supports pagination, search by name/location, and timezone filtering.
    User must have access to the organization.
    """
    try:
        # Verify organization access (done by path parameter validation)
        if search:
            # Search sites
            sites = await site_service.search_sites(
                organization_id=organization_id,
                query=search,
                skip=skip,
                limit=limit
            )
        elif timezone:
            # Filter by timezone
            sites = await site_service.get_sites_by_timezone(
                organization_id=organization_id,
                timezone=timezone
            )
            # Apply pagination to timezone results
            sites = sites[skip:skip + limit]
        else:
            # List all sites
            sites = await site_service.list_sites(
                organization_id=organization_id,
                skip=skip,
                limit=limit
            )

        logger.info(f"Listed {len(sites)} sites for organization {organization_id}")
        return sites

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing sites: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list sites"
        )


@router.get(
    "/{site_id}",
    response_model=SiteResponse,
    summary="Get site details",
    description="Get site details by ID within an organization."
)
async def get_site(
    organization_id: UUID,
    site_id: UUID,
    hierarchy_access = Depends(require_hierarchy_access()),
    site_service: SiteService = Depends(get_site_service)
) -> SiteResponse:
    """
    Get site details by ID.

    User must have access to the organization containing the site.
    """
    try:
        site = await site_service.get_site(site_id)

        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Site not found"
            )

        # Verify site belongs to the specified organization
        if site.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Site does not belong to the specified organization"
            )

        current_user = hierarchy_access['current_user']
        logger.info(f"Retrieved site {site_id} for user {current_user.email}")
        return site

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting site {site_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve site"
        )


@router.get(
    "/{site_id}/stats",
    summary="Get site statistics",
    description="Get site statistics including area and device counts."
)
async def get_site_stats(
    organization_id: UUID,
    site_id: UUID,
    hierarchy_access = Depends(require_hierarchy_access()),
    site_service: SiteService = Depends(get_site_service)
):
    """
    Get site statistics.

    Returns counts of areas, devices, and device status distribution.
    """
    try:
        stats = await site_service.get_site_stats(site_id)

        logger.info(f"Retrieved stats for site {site_id}")
        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting site stats {site_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve site statistics"
        )


@router.post(
    "",
    response_model=SiteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create site",
    description="Create a new site within an organization. Requires operator role or higher."
)
async def create_site(
    organization_id: UUID,
    site_data: SiteCreate,
    current_user: UserResponse = Depends(require_operator_role),
    site_service: SiteService = Depends(get_site_service)
) -> SiteResponse:
    """
    Create a new site within an organization.

    User must have operator role or higher and access to the organization.
    """
    try:
        # Verify organization access through middleware
        from ...middleware.auth_middleware import get_auth_middleware
        from ...services.auth_service import get_auth_service

        auth_service = await get_auth_service()
        auth_middleware = await get_auth_middleware(auth_service)

        has_permission = await auth_middleware.check_organization_permission(
            current_user, organization_id
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for organization"
            )

        site = await site_service.create_site(organization_id, site_data)

        logger.info(f"Created site {site.id} by user {current_user.email}")
        return site

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating site: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create site"
        )


@router.put(
    "/{site_id}",
    response_model=SiteResponse,
    summary="Update site",
    description="Update site details. Requires operator role or higher."
)
async def update_site(
    organization_id: UUID,
    site_id: UUID,
    site_data: SiteUpdate,
    hierarchy_access = Depends(require_hierarchy_access()),
    site_service: SiteService = Depends(get_site_service)
) -> SiteResponse:
    """
    Update site details.

    User must have operator role or higher and access to the organization.
    """
    try:
        current_user = hierarchy_access['current_user']

        # Check if user has operator role or higher
        if current_user.role.value not in ["operator", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operator role or higher required"
            )

        site = await site_service.update_site(site_id, site_data)

        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Site not found"
            )

        logger.info(f"Updated site {site_id} by user {current_user.email}")
        return site

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating site {site_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update site"
        )


@router.delete(
    "/{site_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete site",
    description="Delete site and all its associated data. Requires admin role."
)
async def delete_site(
    organization_id: UUID,
    site_id: UUID,
    current_user: UserResponse = Depends(require_admin_role),
    site_service: SiteService = Depends(get_site_service)
):
    """
    Delete site and all its associated data.

    Only admin users can delete sites.
    This will cascade delete all areas and devices within the site.
    """
    try:
        # Verify organization access
        from ...middleware.auth_middleware import get_auth_middleware
        from ...services.auth_service import get_auth_service

        auth_service = await get_auth_service()
        auth_middleware = await get_auth_middleware(auth_service)

        has_permission = await auth_middleware.check_organization_permission(
            current_user, organization_id
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for organization"
            )

        deleted = await site_service.delete_site(site_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Site not found"
            )

        logger.info(f"Deleted site {site_id} by user {current_user.email}")
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting site {site_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete site"
        )


@router.get(
    "/{site_id}/slug/{slug}",
    response_model=SiteResponse,
    summary="Get site by slug",
    description="Get site details by slug within organization."
)
async def get_site_by_slug(
    organization_id: UUID,
    site_id: UUID,
    slug: str,
    hierarchy_access = Depends(require_hierarchy_access()),
    site_service: SiteService = Depends(get_site_service)
) -> SiteResponse:
    """
    Get site by slug within organization.

    This endpoint is primarily for validation or direct slug-based access.
    """
    try:
        site = await site_service.get_site_by_slug(organization_id, slug)

        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Site not found"
            )

        # Verify the site_id matches
        if site.id != site_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Site ID and slug do not match"
            )

        logger.info(f"Retrieved site by slug {slug}")
        return site

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting site by slug {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve site"
        )