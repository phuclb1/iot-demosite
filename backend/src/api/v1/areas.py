"""
Areas API endpoints.

Provides REST API endpoints for area management within sites
including listing, creation, updating, and deletion of areas.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from ...models.area import AreaCreate, AreaUpdate, AreaResponse
from ...models.user import UserResponse
from ...services.area_service import get_area_service, AreaService
from ...middleware.auth_middleware import (
    require_viewer_role,
    require_operator_role,
    require_admin_role,
    require_hierarchy_access
)


logger = logging.getLogger(__name__)

# Create router for areas
router = APIRouter(
    prefix="/organizations/{organization_id}/sites/{site_id}/areas",
    tags=["areas"]
)


@router.get(
    "",
    response_model=List[AreaResponse],
    summary="List areas in site",
    description="Get list of areas within a site with pagination."
)
async def list_areas(
    organization_id: UUID,
    site_id: UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search query for area name or description"),
    hierarchy_access = Depends(require_hierarchy_access()),
    area_service: AreaService = Depends(get_area_service)
) -> List[AreaResponse]:
    """
    List areas within a site.

    Supports pagination and search by name/description.
    User must have access to the organization.
    """
    try:
        current_user = hierarchy_access['current_user']

        if search:
            # Search areas
            areas = await area_service.search_areas(
                site_id=site_id,
                query=search,
                skip=skip,
                limit=limit
            )
        else:
            # List all areas
            areas = await area_service.list_areas(
                site_id=site_id,
                skip=skip,
                limit=limit
            )

        logger.info(f"Listed {len(areas)} areas for site {site_id}")
        return areas

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing areas: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list areas"
        )


@router.get(
    "/{area_id}",
    response_model=AreaResponse,
    summary="Get area details",
    description="Get area details by ID within a site."
)
async def get_area(
    organization_id: UUID,
    site_id: UUID,
    area_id: UUID,
    hierarchy_access = Depends(require_hierarchy_access()),
    area_service: AreaService = Depends(get_area_service)
) -> AreaResponse:
    """
    Get area details by ID.

    User must have access to the organization containing the area.
    """
    try:
        area = await area_service.get_area(area_id)

        if not area:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Area not found"
            )

        # Verify area belongs to the specified site
        if area.site_id != site_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Area does not belong to the specified site"
            )

        current_user = hierarchy_access['current_user']
        logger.info(f"Retrieved area {area_id} for user {current_user.email}")
        return area

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting area {area_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve area"
        )


@router.get(
    "/{area_id}/stats",
    summary="Get area statistics",
    description="Get area statistics including device counts and status distribution."
)
async def get_area_stats(
    organization_id: UUID,
    site_id: UUID,
    area_id: UUID,
    hierarchy_access = Depends(require_hierarchy_access()),
    area_service: AreaService = Depends(get_area_service)
):
    """
    Get area statistics.

    Returns counts of devices and device status distribution.
    """
    try:
        stats = await area_service.get_area_stats(area_id)

        logger.info(f"Retrieved stats for area {area_id}")
        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting area stats {area_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve area statistics"
        )


@router.get(
    "/{area_id}/hierarchy",
    summary="Get area hierarchy",
    description="Get complete hierarchy information for an area."
)
async def get_area_hierarchy(
    organization_id: UUID,
    site_id: UUID,
    area_id: UUID,
    hierarchy_access = Depends(require_hierarchy_access()),
    area_service: AreaService = Depends(get_area_service)
):
    """
    Get complete hierarchy information for an area.

    Returns area, site, and organization details.
    """
    try:
        hierarchy = await area_service.get_area_hierarchy(area_id)

        logger.info(f"Retrieved hierarchy for area {area_id}")
        return hierarchy

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting area hierarchy {area_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve area hierarchy"
        )


@router.post(
    "",
    response_model=AreaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create area",
    description="Create a new area within a site. Requires operator role or higher."
)
async def create_area(
    organization_id: UUID,
    site_id: UUID,
    area_data: AreaCreate,
    hierarchy_access = Depends(require_hierarchy_access()),
    area_service: AreaService = Depends(get_area_service)
) -> AreaResponse:
    """
    Create a new area within a site.

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

        area = await area_service.create_area(site_id, area_data)

        logger.info(f"Created area {area.id} by user {current_user.email}")
        return area

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating area: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create area"
        )


@router.put(
    "/{area_id}",
    response_model=AreaResponse,
    summary="Update area",
    description="Update area details. Requires operator role or higher."
)
async def update_area(
    organization_id: UUID,
    site_id: UUID,
    area_id: UUID,
    area_data: AreaUpdate,
    hierarchy_access = Depends(require_hierarchy_access()),
    area_service: AreaService = Depends(get_area_service)
) -> AreaResponse:
    """
    Update area details.

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

        area = await area_service.update_area(area_id, area_data)

        if not area:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Area not found"
            )

        logger.info(f"Updated area {area_id} by user {current_user.email}")
        return area

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating area {area_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update area"
        )


@router.delete(
    "/{area_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete area",
    description="Delete area and all its associated devices. Requires admin role."
)
async def delete_area(
    organization_id: UUID,
    site_id: UUID,
    area_id: UUID,
    hierarchy_access = Depends(require_hierarchy_access()),
    area_service: AreaService = Depends(get_area_service)
):
    """
    Delete area and all its associated devices.

    Only admin users can delete areas.
    This will cascade delete all devices within the area.
    """
    try:
        current_user = hierarchy_access['current_user']

        # Check if user has admin role
        if current_user.role.value != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required"
            )

        deleted = await area_service.delete_area(area_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Area not found"
            )

        logger.info(f"Deleted area {area_id} by user {current_user.email}")
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting area {area_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete area"
        )


@router.get(
    "/{area_id}/slug/{slug}",
    response_model=AreaResponse,
    summary="Get area by slug",
    description="Get area details by slug within site."
)
async def get_area_by_slug(
    organization_id: UUID,
    site_id: UUID,
    area_id: UUID,
    slug: str,
    hierarchy_access = Depends(require_hierarchy_access()),
    area_service: AreaService = Depends(get_area_service)
) -> AreaResponse:
    """
    Get area by slug within site.

    This endpoint is primarily for validation or direct slug-based access.
    """
    try:
        area = await area_service.get_area_by_slug(site_id, slug)

        if not area:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Area not found"
            )

        # Verify the area_id matches
        if area.id != area_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Area ID and slug do not match"
            )

        logger.info(f"Retrieved area by slug {slug}")
        return area

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting area by slug {slug}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve area"
        )