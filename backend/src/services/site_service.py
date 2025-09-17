"""
Site service for CRUD operations.

Provides business logic layer for site management including
creation, retrieval, updating, and deletion of sites within organizations.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import HTTPException, Depends

from ..models.site import (
    SiteTable,
    SiteCreate,
    SiteUpdate,
    SiteResponse,
    SiteRepository
)
from ..services.postgresql_service import get_postgresql_service, PostgreSQLService


logger = logging.getLogger(__name__)


class SiteService:
    """Service class for site operations."""

    def __init__(self, db_service: PostgreSQLService):
        """
        Initialize site service.

        Args:
            db_service: PostgreSQL database service
        """
        self.db_service = db_service
        self.repository = SiteRepository()

    async def create_site(
        self,
        organization_id: UUID,
        site_data: SiteCreate
    ) -> SiteResponse:
        """
        Create a new site within an organization.

        Args:
            organization_id: Parent organization UUID
            site_data: Site creation data

        Returns:
            Created site

        Raises:
            HTTPException: If creation fails or slug already exists in organization
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

            # Check if slug already exists within organization
            existing = await self.get_site_by_slug(organization_id, site_data.slug)
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Site with slug '{site_data.slug}' already exists in this organization"
                )

            # Create site using repository
            async with self.db_service.get_connection() as conn:
                site = await self.repository.create(conn, organization_id, site_data)

            logger.info(f"Created site: {site.id} ({site.slug}) in organization {organization_id}")
            return site

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create site: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create site"
            )

    async def get_site(self, site_id: UUID) -> Optional[SiteResponse]:
        """
        Get site by ID.

        Args:
            site_id: Site UUID

        Returns:
            Site if found, None otherwise

        Raises:
            HTTPException: If database operation fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                site = await self.repository.get_by_id(conn, site_id)

            if site:
                logger.debug(f"Retrieved site: {site_id}")

            return site

        except Exception as e:
            logger.error(f"Failed to get site {site_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve site"
            )

    async def get_site_by_slug(
        self,
        organization_id: UUID,
        slug: str
    ) -> Optional[SiteResponse]:
        """
        Get site by slug within organization.

        Args:
            organization_id: Organization UUID
            slug: Site slug

        Returns:
            Site if found, None otherwise

        Raises:
            HTTPException: If database operation fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                site = await self.repository.get_by_slug(conn, organization_id, slug)

            if site:
                logger.debug(f"Retrieved site by slug: {slug} in organization {organization_id}")

            return site

        except Exception as e:
            logger.error(f"Failed to get site by slug {slug}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve site"
            )

    async def list_sites(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[SiteResponse]:
        """
        List sites within organization with pagination.

        Args:
            organization_id: Organization UUID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of sites

        Raises:
            HTTPException: If database operation fails
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

            async with self.db_service.get_connection() as conn:
                sites = await self.repository.list_by_organization(
                    conn, organization_id, skip, limit
                )

            logger.debug(f"Listed {len(sites)} sites for organization {organization_id}")
            return sites

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to list sites: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to list sites"
            )

    async def update_site(
        self,
        site_id: UUID,
        site_data: SiteUpdate
    ) -> Optional[SiteResponse]:
        """
        Update site.

        Args:
            site_id: Site UUID
            site_data: Site update data

        Returns:
            Updated site if found, None otherwise

        Raises:
            HTTPException: If update fails or slug conflicts
        """
        try:
            # Check if site exists
            existing = await self.get_site(site_id)
            if not existing:
                return None

            # Check slug uniqueness if changing
            if site_data.slug and site_data.slug != existing.slug:
                slug_exists = await self.get_site_by_slug(
                    existing.organization_id, site_data.slug
                )
                if slug_exists:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Site with slug '{site_data.slug}' already exists in this organization"
                    )

            # Update site using repository
            async with self.db_service.get_connection() as conn:
                site = await self.repository.update(conn, site_id, site_data)

            if site:
                logger.info(f"Updated site: {site_id}")

            return site

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update site {site_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to update site"
            )

    async def delete_site(self, site_id: UUID) -> bool:
        """
        Delete site.

        Args:
            site_id: Site UUID

        Returns:
            True if deleted, False if not found

        Raises:
            HTTPException: If deletion fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                deleted = await self.repository.delete(conn, site_id)

            if deleted:
                logger.info(f"Deleted site: {site_id}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete site {site_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to delete site"
            )

    async def get_site_stats(self, site_id: UUID) -> Dict[str, Any]:
        """
        Get site statistics.

        Args:
            site_id: Site UUID

        Returns:
            Dictionary with site statistics

        Raises:
            HTTPException: If operation fails
        """
        try:
            # Verify site exists
            site = await self.get_site(site_id)
            if not site:
                raise HTTPException(
                    status_code=404,
                    detail="Site not found"
                )

            # Get statistics from database
            stats_query = """
                SELECT
                    (SELECT COUNT(*) FROM areas WHERE site_id = $1) as area_count,
                    (SELECT COUNT(*) FROM devices d
                     JOIN areas a ON d.area_id = a.id
                     WHERE a.site_id = $1) as device_count,
                    (SELECT COUNT(*) FROM devices d
                     JOIN areas a ON d.area_id = a.id
                     WHERE a.site_id = $1 AND d.status = 'online') as online_device_count
            """

            result = await self.db_service.execute_query_one(stats_query, site_id)

            stats = {
                'site_id': str(site_id),
                'area_count': result['area_count'] if result else 0,
                'device_count': result['device_count'] if result else 0,
                'online_device_count': result['online_device_count'] if result else 0,
                'offline_device_count': 0
            }

            # Calculate offline devices
            stats['offline_device_count'] = stats['device_count'] - stats['online_device_count']

            return stats

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get site stats {site_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to get site statistics"
            )

    async def search_sites(
        self,
        organization_id: UUID,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[SiteResponse]:
        """
        Search sites within organization by name or location.

        Args:
            organization_id: Organization UUID
            query: Search query string
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching sites

        Raises:
            HTTPException: If search fails
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

            search_query = """
                SELECT id, organization_id, name, slug, location, timezone, created_at, updated_at
                FROM sites
                WHERE
                    organization_id = $1 AND (
                        name ILIKE $2 OR
                        location ILIKE $2 OR
                        slug ILIKE $2
                    )
                ORDER BY name
                OFFSET $3 LIMIT $4
            """

            search_pattern = f"%{query}%"
            results = await self.db_service.execute_query(
                search_query, organization_id, search_pattern, skip, limit
            )

            sites = [
                SiteResponse(**dict(row)) for row in results
            ]

            logger.debug(f"Found {len(sites)} sites matching '{query}' in organization {organization_id}")
            return sites

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to search sites with query '{query}': {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to search sites"
            )

    async def get_sites_by_timezone(
        self,
        organization_id: UUID,
        timezone: str
    ) -> List[SiteResponse]:
        """
        Get sites by timezone within organization.

        Args:
            organization_id: Organization UUID
            timezone: IANA timezone name

        Returns:
            List of sites in the specified timezone

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

            timezone_query = """
                SELECT id, organization_id, name, slug, location, timezone, created_at, updated_at
                FROM sites
                WHERE organization_id = $1 AND timezone = $2
                ORDER BY name
            """

            results = await self.db_service.execute_query(
                timezone_query, organization_id, timezone
            )

            sites = [
                SiteResponse(**dict(row)) for row in results
            ]

            logger.debug(f"Found {len(sites)} sites in timezone {timezone}")
            return sites

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get sites by timezone {timezone}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to get sites by timezone"
            )


async def get_site_service(
    db_service: PostgreSQLService = Depends(get_postgresql_service)
) -> SiteService:
    """
    Dependency function to get site service.

    Args:
        db_service: PostgreSQL database service

    Returns:
        Site service instance
    """
    return SiteService(db_service)