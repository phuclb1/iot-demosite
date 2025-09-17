"""
Organization service for CRUD operations.

Provides business logic layer for organization management including
creation, retrieval, updating, and deletion of organizations.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import HTTPException, Depends

from ..models.organization import (
    OrganizationTable,
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationRepository
)
from ..services.postgresql_service import get_postgresql_service, PostgreSQLService


logger = logging.getLogger(__name__)


class OrganizationService:
    """Service class for organization operations."""

    def __init__(self, db_service: PostgreSQLService):
        """
        Initialize organization service.

        Args:
            db_service: PostgreSQL database service
        """
        self.db_service = db_service
        self.repository = OrganizationRepository()

    async def create_organization(
        self,
        organization_data: OrganizationCreate
    ) -> OrganizationResponse:
        """
        Create a new organization.

        Args:
            organization_data: Organization creation data

        Returns:
            Created organization

        Raises:
            HTTPException: If creation fails or slug already exists
        """
        try:
            # Check if slug already exists
            existing = await self.get_organization_by_slug(organization_data.slug)
            if existing:
                raise HTTPException(
                    status_code=400,
                    detail=f"Organization with slug '{organization_data.slug}' already exists"
                )

            # Create organization using repository
            async with self.db_service.get_connection() as conn:
                organization = await self.repository.create(conn, organization_data)

            logger.info(f"Created organization: {organization.id} ({organization.slug})")
            return organization

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create organization: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create organization"
            )

    async def get_organization(self, organization_id: UUID) -> Optional[OrganizationResponse]:
        """
        Get organization by ID.

        Args:
            organization_id: Organization UUID

        Returns:
            Organization if found, None otherwise

        Raises:
            HTTPException: If database operation fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                organization = await self.repository.get_by_id(conn, organization_id)

            if organization:
                logger.debug(f"Retrieved organization: {organization_id}")

            return organization

        except Exception as e:
            logger.error(f"Failed to get organization {organization_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve organization"
            )

    async def get_organization_by_slug(self, slug: str) -> Optional[OrganizationResponse]:
        """
        Get organization by slug.

        Args:
            slug: Organization slug

        Returns:
            Organization if found, None otherwise

        Raises:
            HTTPException: If database operation fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                organization = await self.repository.get_by_slug(conn, slug)

            if organization:
                logger.debug(f"Retrieved organization by slug: {slug}")

            return organization

        except Exception as e:
            logger.error(f"Failed to get organization by slug {slug}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve organization"
            )

    async def list_organizations(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[OrganizationResponse]:
        """
        List organizations with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of organizations

        Raises:
            HTTPException: If database operation fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                organizations = await self.repository.list(conn, skip, limit)

            logger.debug(f"Listed {len(organizations)} organizations")
            return organizations

        except Exception as e:
            logger.error(f"Failed to list organizations: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to list organizations"
            )

    async def update_organization(
        self,
        organization_id: UUID,
        organization_data: OrganizationUpdate
    ) -> Optional[OrganizationResponse]:
        """
        Update organization.

        Args:
            organization_id: Organization UUID
            organization_data: Organization update data

        Returns:
            Updated organization if found, None otherwise

        Raises:
            HTTPException: If update fails or slug conflicts
        """
        try:
            # Check if organization exists
            existing = await self.get_organization(organization_id)
            if not existing:
                return None

            # Check slug uniqueness if changing
            if organization_data.slug and organization_data.slug != existing.slug:
                slug_exists = await self.get_organization_by_slug(organization_data.slug)
                if slug_exists:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Organization with slug '{organization_data.slug}' already exists"
                    )

            # Update organization using repository
            async with self.db_service.get_connection() as conn:
                organization = await self.repository.update(
                    conn, organization_id, organization_data
                )

            if organization:
                logger.info(f"Updated organization: {organization_id}")

            return organization

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update organization {organization_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to update organization"
            )

    async def delete_organization(self, organization_id: UUID) -> bool:
        """
        Delete organization.

        Args:
            organization_id: Organization UUID

        Returns:
            True if deleted, False if not found

        Raises:
            HTTPException: If deletion fails
        """
        try:
            async with self.db_service.get_connection() as conn:
                deleted = await self.repository.delete(conn, organization_id)

            if deleted:
                logger.info(f"Deleted organization: {organization_id}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete organization {organization_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to delete organization"
            )

    async def get_organization_stats(self, organization_id: UUID) -> Dict[str, Any]:
        """
        Get organization statistics.

        Args:
            organization_id: Organization UUID

        Returns:
            Dictionary with organization statistics

        Raises:
            HTTPException: If operation fails
        """
        try:
            # Verify organization exists
            organization = await self.get_organization(organization_id)
            if not organization:
                raise HTTPException(
                    status_code=404,
                    detail="Organization not found"
                )

            # Get statistics from database
            stats_query = """
                SELECT
                    (SELECT COUNT(*) FROM sites WHERE organization_id = $1) as site_count,
                    (SELECT COUNT(*) FROM areas a
                     JOIN sites s ON a.site_id = s.id
                     WHERE s.organization_id = $1) as area_count,
                    (SELECT COUNT(*) FROM devices d
                     JOIN areas a ON d.area_id = a.id
                     JOIN sites s ON a.site_id = s.id
                     WHERE s.organization_id = $1) as device_count,
                    (SELECT COUNT(*) FROM devices d
                     JOIN areas a ON d.area_id = a.id
                     JOIN sites s ON a.site_id = s.id
                     WHERE s.organization_id = $1 AND d.status = 'online') as online_device_count
            """

            result = await self.db_service.execute_query_one(stats_query, organization_id)

            stats = {
                'organization_id': str(organization_id),
                'site_count': result['site_count'] if result else 0,
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
            logger.error(f"Failed to get organization stats {organization_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to get organization statistics"
            )

    async def search_organizations(
        self,
        query: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[OrganizationResponse]:
        """
        Search organizations by name or description.

        Args:
            query: Search query string
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching organizations

        Raises:
            HTTPException: If search fails
        """
        try:
            search_query = """
                SELECT id, name, slug, description, created_at, updated_at
                FROM organizations
                WHERE
                    name ILIKE $1 OR
                    description ILIKE $1 OR
                    slug ILIKE $1
                ORDER BY name
                OFFSET $2 LIMIT $3
            """

            search_pattern = f"%{query}%"
            results = await self.db_service.execute_query(
                search_query, search_pattern, skip, limit
            )

            organizations = [
                OrganizationResponse(**dict(row)) for row in results
            ]

            logger.debug(f"Found {len(organizations)} organizations matching '{query}'")
            return organizations

        except Exception as e:
            logger.error(f"Failed to search organizations with query '{query}': {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to search organizations"
            )


async def get_organization_service(
    db_service: PostgreSQLService = Depends(get_postgresql_service)
) -> OrganizationService:
    """
    Dependency function to get organization service.

    Args:
        db_service: PostgreSQL database service

    Returns:
        Organization service instance
    """
    return OrganizationService(db_service)