"""
Device service for CRUD operations.

Provides business logic layer for device management including
creation, retrieval, updating, and deletion of devices within areas.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import HTTPException, Depends

from ..models.device import (
    DeviceTable,
    DeviceCreate,
    DeviceUpdate,
    DeviceResponse,
    DeviceRepository,
    DeviceStatus
)
from ..services.postgresql_service import get_postgresql_service, PostgreSQLService
from ..services.influxdb_service import get_influxdb_service, InfluxDBService


logger = logging.getLogger(__name__)


class DeviceService:
    """Service class for device operations."""

    def __init__(self, db_service: PostgreSQLService, influx_service: InfluxDBService):
        """
        Initialize device service.

        Args:
            db_service: PostgreSQL database service
            influx_service: InfluxDB service for telemetry data
        """
        self.db_service = db_service
        self.influx_service = influx_service
        self.repository = DeviceRepository()

    async def create_device(
        self,
        area_id: UUID,
        device_data: DeviceCreate
    ) -> DeviceResponse:
        """
        Create a new device within an area.

        Args:
            area_id: Parent area UUID
            device_data: Device creation data

        Returns:
            Created device

        Raises:
            HTTPException: If creation fails or MAC address already exists
        """
        try:
            # Verify area exists
            area_check_query = "SELECT id FROM areas WHERE id = $1"
            area_exists = await self.db_service.execute_query_one(area_check_query, area_id)
            if not area_exists:
                raise HTTPException(
                    status_code=404,
                    detail="Area not found"
                )

            # Check if MAC address already exists (if provided)
            if device_data.mac_address:
                existing_mac = await self.get_device_by_mac_address(device_data.mac_address)
                if existing_mac:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Device with MAC address '{device_data.mac_address}' already exists"
                    )

            # Create device using repository
            async with self.db_service.get_connection() as conn:
                device = await self.repository.create(conn, area_id, device_data)

            logger.info(f"Created device: {device.id} ({device.name}) in area {area_id}")
            return device

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create device: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create device"
            )

    async def get_device(self, device_id: UUID) -> Optional[DeviceResponse]:
        """
        Get device by ID.

        Args:
            device_id: Device UUID

        Returns:
            Device if found, None otherwise

        Raises:
            HTTPException: If database operation fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                device = await self.repository.get_by_id(conn, device_id)

            if device:
                logger.debug(f"Retrieved device: {device_id}")

            return device

        except Exception as e:
            logger.error(f"Failed to get device {device_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve device"
            )

    async def get_device_by_mac_address(self, mac_address: str) -> Optional[DeviceResponse]:
        """
        Get device by MAC address.

        Args:
            mac_address: Device MAC address

        Returns:
            Device if found, None otherwise

        Raises:
            HTTPException: If database operation fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                device = await self.repository.get_by_mac_address(conn, mac_address)

            if device:
                logger.debug(f"Retrieved device by MAC: {mac_address}")

            return device

        except Exception as e:
            logger.error(f"Failed to get device by MAC {mac_address}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve device"
            )

    async def list_devices(
        self,
        area_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status_filter: Optional[DeviceStatus] = None
    ) -> List[DeviceResponse]:
        """
        List devices within area with pagination and optional status filter.

        Args:
            area_id: Area UUID
            skip: Number of records to skip
            limit: Maximum number of records to return
            status_filter: Optional device status filter

        Returns:
            List of devices

        Raises:
            HTTPException: If database operation fails
        """
        try:
            # Verify area exists
            area_check_query = "SELECT id FROM areas WHERE id = $1"
            area_exists = await self.db_service.execute_query_one(area_check_query, area_id)
            if not area_exists:
                raise HTTPException(
                    status_code=404,
                    detail="Area not found"
                )

            async with self.db_service.get_connection() as conn:
                devices = await self.repository.list_by_area(
                    conn, area_id, skip, limit, status_filter
                )

            logger.debug(f"Listed {len(devices)} devices for area {area_id}")
            return devices

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to list devices"
            )

    async def update_device(
        self,
        device_id: UUID,
        device_data: DeviceUpdate
    ) -> Optional[DeviceResponse]:
        """
        Update device.

        Args:
            device_id: Device UUID
            device_data: Device update data

        Returns:
            Updated device if found, None otherwise

        Raises:
            HTTPException: If update fails or MAC address conflicts
        """
        try:
            # Check if device exists
            existing = await self.get_device(device_id)
            if not existing:
                return None

            # Check MAC address uniqueness if changing
            if (device_data.mac_address and
                device_data.mac_address != existing.mac_address):
                mac_exists = await self.get_device_by_mac_address(device_data.mac_address)
                if mac_exists:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Device with MAC address '{device_data.mac_address}' already exists"
                    )

            # Update device using repository
            async with self.db_service.get_connection() as conn:
                device = await self.repository.update(conn, device_id, device_data)

            if device:
                logger.info(f"Updated device: {device_id}")

            return device

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update device {device_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to update device"
            )

    async def update_device_status(
        self,
        device_id: UUID,
        status: DeviceStatus,
        update_last_seen: bool = True
    ) -> Optional[DeviceResponse]:
        """
        Update device status and optionally last seen timestamp.

        Args:
            device_id: Device UUID
            status: New device status
            update_last_seen: Whether to update last_seen timestamp

        Returns:
            Updated device if found, None otherwise

        Raises:
            HTTPException: If update fails
        """
        try:
            # Check if device exists
            existing = await self.get_device(device_id)
            if not existing:
                return None

            # Prepare update data
            update_data = DeviceUpdate(status=status)
            if update_last_seen and status == DeviceStatus.ONLINE:
                update_data.last_seen = datetime.utcnow()

            # Update device
            device = await self.update_device(device_id, update_data)

            # Write status to InfluxDB for tracking
            if device and self.influx_service.is_initialized:
                try:
                    await self.influx_service.write_point(
                        measurement="device_status_snapshot",
                        tags={"device_id": str(device_id)},
                        fields={
                            "status": status.value,
                            "uptime_minutes": await self.calculate_uptime_minutes(device_id)
                        },
                        bucket="device_status"
                    )
                except Exception as e:
                    logger.warning(f"Failed to write device status to InfluxDB: {e}")

            return device

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update device status {device_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to update device status"
            )

    async def delete_device(self, device_id: UUID) -> bool:
        """
        Delete device.

        Args:
            device_id: Device UUID

        Returns:
            True if deleted, False if not found

        Raises:
            HTTPException: If deletion fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                deleted = await self.repository.delete(conn, device_id)

            if deleted:
                logger.info(f"Deleted device: {device_id}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete device {device_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to delete device"
            )

    async def search_devices(
        self,
        area_id: UUID,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[DeviceResponse]:
        """
        Search devices within area by name or model.

        Args:
            area_id: Area UUID
            query: Search query string
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching devices

        Raises:
            HTTPException: If search fails
        """
        try:
            # Verify area exists
            area_check_query = "SELECT id FROM areas WHERE id = $1"
            area_exists = await self.db_service.execute_query_one(area_check_query, area_id)
            if not area_exists:
                raise HTTPException(
                    status_code=404,
                    detail="Area not found"
                )

            search_query = """
                SELECT id, area_id, name, model, firmware_version, mac_address,
                       last_seen, status, created_at, updated_at
                FROM devices
                WHERE
                    area_id = $1 AND (
                        name ILIKE $2 OR
                        model ILIKE $2 OR
                        mac_address ILIKE $2
                    )
                ORDER BY name
                OFFSET $3 LIMIT $4
            """

            search_pattern = f"%{query}%"
            results = await self.db_service.execute_query(
                search_query, area_id, search_pattern, skip, limit
            )

            devices = [
                DeviceResponse(**dict(row)) for row in results
            ]

            logger.debug(f"Found {len(devices)} devices matching '{query}' in area {area_id}")
            return devices

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to search devices with query '{query}': {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to search devices"
            )

    async def get_device_hierarchy(self, device_id: UUID) -> Dict[str, Any]:
        """
        Get complete hierarchy information for a device.

        Args:
            device_id: Device UUID

        Returns:
            Dictionary with device hierarchy information

        Raises:
            HTTPException: If operation fails
        """
        try:
            # Get device with full hierarchy
            hierarchy_query = """
                SELECT
                    d.id as device_id,
                    d.name as device_name,
                    d.model as device_model,
                    d.status as device_status,
                    a.id as area_id,
                    a.name as area_name,
                    a.slug as area_slug,
                    s.id as site_id,
                    s.name as site_name,
                    s.slug as site_slug,
                    s.timezone as site_timezone,
                    o.id as organization_id,
                    o.name as organization_name,
                    o.slug as organization_slug
                FROM devices d
                JOIN areas a ON d.area_id = a.id
                JOIN sites s ON a.site_id = s.id
                JOIN organizations o ON s.organization_id = o.id
                WHERE d.id = $1
            """

            result = await self.db_service.execute_query_one(hierarchy_query, device_id)

            if not result:
                raise HTTPException(
                    status_code=404,
                    detail="Device not found"
                )

            hierarchy = {
                'device': {
                    'id': str(result['device_id']),
                    'name': result['device_name'],
                    'model': result['device_model'],
                    'status': result['device_status']
                },
                'area': {
                    'id': str(result['area_id']),
                    'name': result['area_name'],
                    'slug': result['area_slug']
                },
                'site': {
                    'id': str(result['site_id']),
                    'name': result['site_name'],
                    'slug': result['site_slug'],
                    'timezone': result['site_timezone']
                },
                'organization': {
                    'id': str(result['organization_id']),
                    'name': result['organization_name'],
                    'slug': result['organization_slug']
                }
            }

            return hierarchy

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get device hierarchy {device_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to get device hierarchy"
            )

    async def calculate_uptime_minutes(self, device_id: UUID) -> float:
        """
        Calculate device uptime in minutes from InfluxDB data.

        Args:
            device_id: Device UUID

        Returns:
            Uptime in minutes

        Raises:
            HTTPException: If calculation fails
        """
        try:
            if not self.influx_service.is_initialized:
                return 0.0

            # Get device status data from last 24 hours
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=24)

            status_data = await self.influx_service.query_historical(
                measurement="device_status_snapshot",
                device_id=str(device_id),
                start_time=start_time,
                end_time=end_time,
                fields=["status"],
                bucket="device_status"
            )

            if not status_data:
                return 0.0

            # Calculate uptime based on status changes
            online_minutes = 0.0
            last_time = start_time
            last_status = "offline"

            for point in status_data:
                current_time = point.get('time', point.get('_time'))
                current_status = point.get('value', point.get('_value'))

                if last_status == "online":
                    duration = (current_time - last_time).total_seconds() / 60
                    online_minutes += duration

                last_time = current_time
                last_status = current_status

            # Add time from last status change to now if online
            if last_status == "online":
                duration = (end_time - last_time).total_seconds() / 60
                online_minutes += duration

            return round(online_minutes, 2)

        except Exception as e:
            logger.error(f"Failed to calculate uptime for device {device_id}: {e}")
            return 0.0


async def get_device_service(
    db_service: PostgreSQLService = Depends(get_postgresql_service),
    influx_service: InfluxDBService = Depends(get_influxdb_service)
) -> DeviceService:
    """
    Dependency function to get device service.

    Args:
        db_service: PostgreSQL database service
        influx_service: InfluxDB service

    Returns:
        Device service instance
    """
    return DeviceService(db_service, influx_service)