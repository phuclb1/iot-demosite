"""
Contract test for GET /api/v1/organizations/{org_id}/sites endpoint.

This test validates that the endpoint:
- Returns 200 with proper JSON structure when authenticated and authorized
- Returns 401 when not authenticated
- Returns 403 when authenticated but not authorized for organization
- Validates UUID format for path parameters
- Follows the OpenAPI schema specification
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import uuid


class TestSitesGetContract:
    """Contract tests for GET /api/v1/organizations/{org_id}/sites endpoint."""

    @pytest.mark.asyncio
    async def test_sites_get_success_schema(self, async_client: AsyncClient):
        """Test that GET /api/v1/organizations/{org_id}/sites returns proper schema when authenticated."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Mock valid UUID for organization ID
        org_id = "550e8400-e29b-41d4-a716-446655440000"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        response = await async_client.get(f"/api/v1/organizations/{org_id}/sites", headers=headers)

        # Contract validation - should return 200 with proper JSON structure
        assert response.status_code == 200

        json_data = response.json()

        # Validate response structure per OpenAPI schema
        assert "sites" in json_data
        assert "total" in json_data
        assert isinstance(json_data["sites"], list)
        assert isinstance(json_data["total"], int)

        # If sites exist, validate site schema
        if json_data["sites"]:
            site = json_data["sites"][0]
            required_fields = ["id", "organization_id", "name", "slug", "timezone", "created_at", "updated_at"]
            for field in required_fields:
                assert field in site

            # Validate UUID format for id and organization_id
            assert uuid.UUID(site["id"])  # Should not raise ValueError
            assert uuid.UUID(site["organization_id"])  # Should not raise ValueError

            # Validate string fields
            assert isinstance(site["name"], str)
            assert isinstance(site["slug"], str)
            assert isinstance(site["timezone"], str)
            assert len(site["name"]) <= 255

            # Validate slug pattern (a-z0-9-)
            import re
            assert re.match(r'^[a-z0-9-]+$', site["slug"])

            # Validate datetime format
            from datetime import datetime
            datetime.fromisoformat(site["created_at"].replace('Z', '+00:00'))
            datetime.fromisoformat(site["updated_at"].replace('Z', '+00:00'))

            # Validate organization_id matches the path parameter
            assert site["organization_id"] == org_id

            # Validate optional location field if present
            if "location" in site and site["location"] is not None:
                assert isinstance(site["location"], str)

    @pytest.mark.asyncio
    async def test_sites_get_unauthorized(self, async_client: AsyncClient):
        """Test that GET /api/v1/organizations/{org_id}/sites returns 401 when not authenticated."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        org_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.get(f"/api/v1/organizations/{org_id}/sites")

        # Contract validation - should return 401 when no auth header
        assert response.status_code == 401

        json_data = response.json()

        # Validate error response schema per OpenAPI
        assert "error" in json_data
        assert "code" in json_data
        assert json_data["code"] == "UNAUTHORIZED"
        assert isinstance(json_data["error"], str)

    @pytest.mark.asyncio
    async def test_sites_get_forbidden(self, async_client: AsyncClient):
        """Test that GET /api/v1/organizations/{org_id}/sites returns 403 when not authorized for organization."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Mock valid UUID for organization ID that user doesn't have access to
        org_id = "550e8400-e29b-41d4-a716-446655440001"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        response = await async_client.get(f"/api/v1/organizations/{org_id}/sites", headers=headers)

        # Contract validation - should return 403 when not authorized
        assert response.status_code == 403

        json_data = response.json()

        # Validate error response schema per OpenAPI
        assert "error" in json_data
        assert "code" in json_data
        assert json_data["code"] == "FORBIDDEN"
        assert isinstance(json_data["error"], str)

    @pytest.mark.asyncio
    async def test_sites_get_invalid_org_id_format(self, async_client: AsyncClient):
        """Test that GET /api/v1/organizations/{org_id}/sites returns 422 with invalid UUID format."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}
        invalid_org_id = "not-a-uuid"

        response = await async_client.get(f"/api/v1/organizations/{invalid_org_id}/sites", headers=headers)

        # Contract validation - should return 422 for invalid UUID format
        assert response.status_code == 422

    def test_sites_get_content_type(self, client: TestClient):
        """Test that GET /api/v1/organizations/{org_id}/sites returns application/json content-type."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        org_id = "550e8400-e29b-41d4-a716-446655440000"
        headers = {"Authorization": "Bearer mock-jwt-token"}
        response = client.get(f"/api/v1/organizations/{org_id}/sites", headers=headers)

        # Content-type validation per OpenAPI spec
        assert response.headers.get("content-type") == "application/json"