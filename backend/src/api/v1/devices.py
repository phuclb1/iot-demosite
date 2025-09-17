"""
Devices API endpoints.

Provides REST API endpoints for device management within areas
including listing, creation, updating, and deletion of devices.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from ...models.device import DeviceCreate, DeviceUpdate, DeviceResponse, DeviceStatus
from ...models.user import UserResponse
from ...services.device_service import get_device_service, DeviceService
from ...middleware.auth_middleware import (
    require_viewer_role,
    require_operator_role,
    require_admin_role,
    require_hierarchy_access
)


logger = logging.getLogger(__name__)

# Create router for devices
router = APIRouter(
    prefix="/organizations/{organization_id}/sites/{site_id}/areas/{area_id}/devices",
    tags=["devices"]
)


@router.get(
    "",
    response_model=List[DeviceResponse],
    summary="List devices in area",
    description="Get list of devices within an area with pagination and filtering."
)
async def list_devices(
    organization_id: UUID,
    site_id: UUID,
    area_id: UUID,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    search: Optional[str] = Query(None, description="Search query for device name, model, or MAC address"),
    status: Optional[DeviceStatus] = Query(None, description="Filter by device status"),
    hierarchy_access = Depends(require_hierarchy_access()),
    device_service: DeviceService = Depends(get_device_service)
) -> List[DeviceResponse]:
    """
    List devices within an area.

    Supports pagination, search, and status filtering.
    User must have access to the organization.
    """
    try:
        current_user = hierarchy_access['current_user']

        if search:
            # Search devices
            devices = await device_service.search_devices(
                area_id=area_id,
                query=search,
                skip=skip,
                limit=limit
            )
        else:
            # List all devices with optional status filter
            devices = await device_service.list_devices(
                area_id=area_id,
                skip=skip,
                limit=limit,
                status_filter=status
            )

        logger.info(f"Listed {len(devices)} devices for area {area_id}")
        return devices

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list devices"
        )


@router.get(
    "/{device_id}",
    response_model=DeviceResponse,
    summary="Get device details",
    description="Get device details by ID within an area."
)
async def get_device(
    organization_id: UUID,
    site_id: UUID,
    area_id: UUID,
    device_id: UUID,
    hierarchy_access = Depends(require_hierarchy_access()),
    device_service: DeviceService = Depends(get_device_service)
) -> DeviceResponse:
    """
    Get device details by ID.

    User must have access to the organization containing the device.
    """
    try:
        device = await device_service.get_device(device_id)

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        # Verify device belongs to the specified area
        if device.area_id != area_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Device does not belong to the specified area"
            )

        current_user = hierarchy_access['current_user']
        logger.info(f"Retrieved device {device_id} for user {current_user.email}")
        return device

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve device"
        )


@router.get(
    "/{device_id}/hierarchy",
    summary="Get device hierarchy",
    description="Get complete hierarchy information for a device."
)
async def get_device_hierarchy(
    organization_id: UUID,
    site_id: UUID,
    area_id: UUID,
    device_id: UUID,
    hierarchy_access = Depends(require_hierarchy_access()),
    device_service: DeviceService = Depends(get_device_service)
):
    """
    Get complete hierarchy information for a device.

    Returns device, area, site, and organization details.
    """
    try:
        hierarchy = await device_service.get_device_hierarchy(device_id)

        logger.info(f"Retrieved hierarchy for device {device_id}")
        return hierarchy

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device hierarchy {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve device hierarchy"
        )


@router.post(
    "",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create device",
    description="Create a new device within an area. Requires operator role or higher."
)
async def create_device(
    organization_id: UUID,
    site_id: UUID,
    area_id: UUID,
    device_data: DeviceCreate,
    hierarchy_access = Depends(require_hierarchy_access()),
    device_service: DeviceService = Depends(get_device_service)
) -> DeviceResponse:
    """
    Create a new device within an area.

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

        device = await device_service.create_device(area_id, device_data)

        logger.info(f"Created device {device.id} by user {current_user.email}")
        return device

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating device: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create device"
        )


@router.put(
    "/{device_id}",
    response_model=DeviceResponse,
    summary="Update device",
    description="Update device details. Requires operator role or higher."
)
async def update_device(
    organization_id: UUID,
    site_id: UUID,
    area_id: UUID,
    device_id: UUID,
    device_data: DeviceUpdate,
    hierarchy_access = Depends(require_hierarchy_access()),
    device_service: DeviceService = Depends(get_device_service)
) -> DeviceResponse:
    """
    Update device details.

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

        device = await device_service.update_device(device_id, device_data)

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        logger.info(f"Updated device {device_id} by user {current_user.email}")
        return device

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update device"
        )


@router.put(
    "/{device_id}/status",
    response_model=DeviceResponse,
    summary="Update device status",
    description="Update device status. Requires operator role or higher."
)
async def update_device_status(
    organization_id: UUID,
    site_id: UUID,
    area_id: UUID,
    device_id: UUID,
    status: DeviceStatus,
    hierarchy_access = Depends(require_hierarchy_access()),
    device_service: DeviceService = Depends(get_device_service)
) -> DeviceResponse:
    """
    Update device status.

    User must have operator role or higher and access to the organization.
    This also updates the last_seen timestamp if status is set to online.
    """
    try:
        current_user = hierarchy_access['current_user']

        # Check if user has operator role or higher
        if current_user.role.value not in ["operator", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operator role or higher required"
            )

        device = await device_service.update_device_status(
            device_id=device_id,
            status=status,
            update_last_seen=True
        )

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        logger.info(f"Updated device {device_id} status to {status.value} by user {current_user.email}")
        return device

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating device status {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update device status"
        )


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete device",
    description="Delete device and all its associated telemetry data. Requires admin role."
)
async def delete_device(
    organization_id: UUID,
    site_id: UUID,
    area_id: UUID,
    device_id: UUID,
    hierarchy_access = Depends(require_hierarchy_access()),
    device_service: DeviceService = Depends(get_device_service)
):
    """
    Delete device and all its associated telemetry data.

    Only admin users can delete devices.
    This will remove the device and all its telemetry data.
    """
    try:
        current_user = hierarchy_access['current_user']

        # Check if user has admin role
        if current_user.role.value != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required"
            )

        deleted = await device_service.delete_device(device_id)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        logger.info(f"Deleted device {device_id} by user {current_user.email}")
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content=None
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete device"
        )


@router.get(
    "/mac/{mac_address}",
    response_model=DeviceResponse,
    summary="Get device by MAC address",
    description="Get device details by MAC address."
)
async def get_device_by_mac_address(
    organization_id: UUID,
    site_id: UUID,
    area_id: UUID,
    mac_address: str,
    hierarchy_access = Depends(require_hierarchy_access()),
    device_service: DeviceService = Depends(get_device_service)
) -> DeviceResponse:
    """
    Get device by MAC address.

    This endpoint is useful for device identification and management.
    """
    try:
        device = await device_service.get_device_by_mac_address(mac_address)

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found"
            )

        # Verify device belongs to the specified area
        if device.area_id != area_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Device does not belong to the specified area"
            )

        logger.info(f"Retrieved device by MAC address {mac_address}")
        return device

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device by MAC {mac_address}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve device"
        )


@router.get(
    "/{device_id}/uptime",
    summary="Get device uptime",
    description="Get device uptime statistics from telemetry data."
)
async def get_device_uptime(
    organization_id: UUID,
    site_id: UUID,
    area_id: UUID,
    device_id: UUID,
    hierarchy_access = Depends(require_hierarchy_access()),
    device_service: DeviceService = Depends(get_device_service)
):
    """
    Get device uptime statistics.

    Returns uptime calculation based on device status tracking data.
    """
    try:
        uptime_minutes = await device_service.calculate_uptime_minutes(device_id)

        # Convert to hours and percentage (assuming 24h period)
        uptime_hours = uptime_minutes / 60
        uptime_percentage = (uptime_minutes / (24 * 60)) * 100

        result = {
            "device_id": str(device_id),
            "uptime_minutes": uptime_minutes,
            "uptime_hours": round(uptime_hours, 2),
            "uptime_percentage": round(uptime_percentage, 2),
            "period_hours": 24
        }

        logger.info(f"Retrieved uptime for device {device_id}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting device uptime {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve device uptime"
        )