"""
Area service for CRUD operations.

Provides business logic layer for area management including
creation, retrieval, updating, and deletion of areas within sites.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import HTTPException, Depends

from ..models.area import (
    AreaTable,
    AreaCreate,
    AreaUpdate,
    AreaResponse,
    AreaRepository
)
from ..services.postgresql_service import get_postgresql_service, PostgreSQLService


logger = logging.getLogger(__name__)


class AreaService:
    """Service class for area operations."""

    def __init__(self, db_service: PostgreSQLService):
        """
        Initialize area service.

        Args:
            db_service: PostgreSQL database service
        """
        self.db_service = db_service
        self.repository = AreaRepository()

    async def create_area(
        self,
        site_id: UUID,
        area_data: AreaCreate
    ) -> AreaResponse:
        """
        Create a new area within a site.

        Args:
            site_id: Parent site UUID
            area_data: Area creation data

        Returns:
            Created area

        Raises:
            HTTPException: If creation fails or slug already exists in site
        """
        try:
            # Verify site exists
            site_check_query = "SELECT id FROM sites WHERE id = $1"
            site_exists = await self.db_service.execute_query_one(site_check_query, site_id)
            if not site_exists:
                raise HTTPException(
                    status_code=404,
                    detail="Site not found"
                )

            # Check if slug already exists within site
            existing = await self.get_area_by_slug(site_id, area_data.slug)
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Area with slug '{area_data.slug}' already exists in this site"
                )

            # Create area using repository
            async with self.db_service.get_connection() as conn:
                area = await self.repository.create(conn, site_id, area_data)

            logger.info(f"Created area: {area.id} ({area.slug}) in site {site_id}")
            return area

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create area: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create area"
            )

    async def get_area(self, area_id: UUID) -> Optional[AreaResponse]:
        """
        Get area by ID.

        Args:
            area_id: Area UUID

        Returns:
            Area if found, None otherwise

        Raises:
            HTTPException: If database operation fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                area = await self.repository.get_by_id(conn, area_id)

            if area:
                logger.debug(f"Retrieved area: {area_id}")

            return area

        except Exception as e:
            logger.error(f"Failed to get area {area_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve area"
            )

    async def get_area_by_slug(
        self,
        site_id: UUID,
        slug: str
    ) -> Optional[AreaResponse]:
        """
        Get area by slug within site.

        Args:
            site_id: Site UUID
            slug: Area slug

        Returns:
            Area if found, None otherwise

        Raises:
            HTTPException: If database operation fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                area = await self.repository.get_by_slug(conn, site_id, slug)

            if area:
                logger.debug(f"Retrieved area by slug: {slug} in site {site_id}")

            return area

        except Exception as e:
            logger.error(f"Failed to get area by slug {slug}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve area"
            )

    async def list_areas(
        self,
        site_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[AreaResponse]:
        """
        List areas within site with pagination.

        Args:
            site_id: Site UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of areas

        Raises:
            HTTPException: If database operation fails
        """
        try:
            # Verify site exists
            site_check_query = "SELECT id FROM sites WHERE id = $1"
            site_exists = await self.db_service.execute_query_one(site_check_query, site_id)
            if not site_exists:
                raise HTTPException(
                    status_code=404,
                    detail="Site not found"
                )

            async with self.db_service.get_connection() as conn:
                areas = await self.repository.list_by_site(conn, site_id, skip, limit)

            logger.debug(f"Listed {len(areas)} areas for site {site_id}")
            return areas

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to list areas: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to list areas"
            )

    async def update_area(
        self,
        area_id: UUID,
        area_data: AreaUpdate
    ) -> Optional[AreaResponse]:
        """
        Update area.

        Args:
            area_id: Area UUID
            area_data: Area update data

        Returns:
            Updated area if found, None otherwise

        Raises:
            HTTPException: If update fails or slug conflicts
        """
        try:
            # Check if area exists
            existing = await self.get_area(area_id)
            if not existing:
                return None

            # Check slug uniqueness if changing
            if area_data.slug and area_data.slug != existing.slug:
                slug_exists = await self.get_area_by_slug(existing.site_id, area_data.slug)
                if slug_exists:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Area with slug '{area_data.slug}' already exists in this site"
                    )

            # Update area using repository
            async with self.db_service.get_connection() as conn:
                area = await self.repository.update(conn, area_id, area_data)

            if area:
                logger.info(f"Updated area: {area_id}")

            return area

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update area {area_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to update area"
            )

    async def delete_area(self, area_id: UUID) -> bool:
        """
        Delete area.

        Args:
            area_id: Area UUID

        Returns:
            True if deleted, False if not found

        Raises:
            HTTPException: If deletion fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                deleted = await self.repository.delete(conn, area_id)

            if deleted:
                logger.info(f"Deleted area: {area_id}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete area {area_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to delete area"
            )

    async def get_area_stats(self, area_id: UUID) -> Dict[str, Any]:
        """
        Get area statistics.

        Args:
            area_id: Area UUID

        Returns:
            Dictionary with area statistics

        Raises:
            HTTPException: If operation fails
        """
        try:
            # Verify area exists
            area = await self.get_area(area_id)
            if not area:
                raise HTTPException(
                    status_code=404,
                    detail="Area not found"
                )

            # Get statistics from database
            stats_query = """
                SELECT
                    (SELECT COUNT(*) FROM devices WHERE area_id = $1) as device_count,
                    (SELECT COUNT(*) FROM devices WHERE area_id = $1 AND status = 'online') as online_device_count,
                    (SELECT COUNT(*) FROM devices WHERE area_id = $1 AND status = 'offline') as offline_device_count,
                    (SELECT COUNT(*) FROM devices WHERE area_id = $1 AND status = 'maintenance') as maintenance_device_count
            """

            result = await self.db_service.execute_query_one(stats_query, area_id)

            stats = {
                'area_id': str(area_id),
                'device_count': result['device_count'] if result else 0,
                'online_device_count': result['online_device_count'] if result else 0,
                'offline_device_count': result['offline_device_count'] if result else 0,
                'maintenance_device_count': result['maintenance_device_count'] if result else 0
            }

            return stats

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get area stats {area_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to get area statistics"
            )

    async def search_areas(
        self,
        site_id: UUID,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[AreaResponse]:
        """
        Search areas within site by name or description.

        Args:
            site_id: Site UUID
            query: Search query string
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching areas

        Raises:
            HTTPException: If search fails
        """
        try:
            # Verify site exists
            site_check_query = "SELECT id FROM sites WHERE id = $1"
            site_exists = await self.db_service.execute_query_one(site_check_query, site_id)
            if not site_exists:
                raise HTTPException(
                    status_code=404,
                    detail="Site not found"
                )

            search_query = """
                SELECT id, site_id, name, slug, description, created_at, updated_at
                FROM areas
                WHERE
                    site_id = $1 AND (
                        name ILIKE $2 OR
                        description ILIKE $2 OR
                        slug ILIKE $2
                    )
                ORDER BY name
                OFFSET $3 LIMIT $4
            """

            search_pattern = f"%{query}%"
            results = await self.db_service.execute_query(
                search_query, site_id, search_pattern, skip, limit
            )

            areas = [
                AreaResponse(**dict(row)) for row in results
            ]

            logger.debug(f"Found {len(areas)} areas matching '{query}' in site {site_id}")
            return areas

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to search areas with query '{query}': {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to search areas"
            )

    async def get_area_hierarchy(self, area_id: UUID) -> Dict[str, Any]:
        """
        Get complete hierarchy information for an area.

        Args:
            area_id: Area UUID

        Returns:
            Dictionary with area hierarchy information

        Raises:
            HTTPException: If operation fails
        """
        try:
            # Get area with full hierarchy
            hierarchy_query = """
                SELECT
                    a.id as area_id,
                    a.name as area_name,
                    a.slug as area_slug,
                    a.description as area_description,
                    s.id as site_id,
                    s.name as site_name,
                    s.slug as site_slug,
                    s.location as site_location,
                    s.timezone as site_timezone,
                    o.id as organization_id,
                    o.name as organization_name,
                    o.slug as organization_slug
                FROM areas a
                JOIN sites s ON a.site_id = s.id
                JOIN organizations o ON s.organization_id = o.id
                WHERE a.id = $1
            """

            result = await self.db_service.execute_query_one(hierarchy_query, area_id)

            if not result:
                raise HTTPException(
                    status_code=404,
                    detail="Area not found"
                )

            hierarchy = {
                'area': {
                    'id': str(result['area_id']),
                    'name': result['area_name'],
                    'slug': result['area_slug'],
                    'description': result['area_description']
                },
                'site': {
                    'id': str(result['site_id']),
                    'name': result['site_name'],
                    'slug': result['site_slug'],
                    'location': result['site_location'],
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
            logger.error(f"Failed to get area hierarchy {area_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to get area hierarchy"
            )


async def get_area_service(
    db_service: PostgreSQLService = Depends(get_postgresql_service)
) -> AreaService:
    """
    Dependency function to get area service.

    Args:
        db_service: PostgreSQL database service

    Returns:
        Area service instance
    """
    return AreaService(db_service)