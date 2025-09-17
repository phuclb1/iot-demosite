"""
Contract test for GET /api/v1/organizations/{org_id}/sites/{site_id}/areas endpoint.

This test validates that the endpoint:
- Returns 200 with proper JSON structure when authenticated and authorized
- Returns 401 when not authenticated
- Returns 403 when authenticated but not authorized
- Validates UUID format for path parameters
- Follows the OpenAPI schema specification
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import uuid


class TestAreasGetContract:
    """Contract tests for GET /api/v1/organizations/{org_id}/sites/{site_id}/areas endpoint."""

    @pytest.mark.asyncio
    async def test_areas_get_success_schema(self, async_client: AsyncClient):
        """Test that GET /api/v1/organizations/{org_id}/sites/{site_id}/areas returns proper schema when authenticated."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Mock valid UUIDs for path parameters
        org_id = "550e8400-e29b-41d4-a716-446655440000"
        site_id = "550e8400-e29b-41d4-a716-446655440001"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        response = await async_client.get(
            f"/api/v1/organizations/{org_id}/sites/{site_id}/areas",
            headers=headers
        )

        # Contract validation - should return 200 with proper JSON structure
        assert response.status_code == 200

        json_data = response.json()

        # Validate response structure per OpenAPI schema
        assert "areas" in json_data
        assert isinstance(json_data["areas"], list)

        # If areas exist, validate area schema
        if json_data["areas"]:
            area = json_data["areas"][0]
            required_fields = ["id", "site_id", "name", "slug", "created_at", "updated_at"]
            for field in required_fields:
                assert field in area

            # Validate UUID format for id and site_id
            assert uuid.UUID(area["id"])  # Should not raise ValueError
            assert uuid.UUID(area["site_id"])  # Should not raise ValueError

            # Validate string fields
            assert isinstance(area["name"], str)
            assert isinstance(area["slug"], str)
            assert len(area["name"]) <= 255

            # Validate slug pattern (a-z0-9-)
            import re
            assert re.match(r'^[a-z0-9-]+$', area["slug"])

            # Validate datetime format
            from datetime import datetime
            datetime.fromisoformat(area["created_at"].replace('Z', '+00:00'))
            datetime.fromisoformat(area["updated_at"].replace('Z', '+00:00'))

            # Validate site_id matches the path parameter
            assert area["site_id"] == site_id

            # Validate optional description field if present
            if "description" in area and area["description"] is not None:
                assert isinstance(area["description"], str)

    @pytest.mark.asyncio
    async def test_areas_get_unauthorized(self, async_client: AsyncClient):
        """Test that GET /api/v1/organizations/{org_id}/sites/{site_id}/areas returns 401 when not authenticated."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        org_id = "550e8400-e29b-41d4-a716-446655440000"
        site_id = "550e8400-e29b-41d4-a716-446655440001"

        response = await async_client.get(f"/api/v1/organizations/{org_id}/sites/{site_id}/areas")

        # Contract validation - should return 401 when no auth header
        assert response.status_code == 401

        json_data = response.json()

        # Validate error response schema per OpenAPI
        assert "error" in json_data
        assert "code" in json_data
        assert json_data["code"] == "UNAUTHORIZED"
        assert isinstance(json_data["error"], str)

    @pytest.mark.asyncio
    async def test_areas_get_forbidden(self, async_client: AsyncClient):
        """Test that GET /api/v1/organizations/{org_id}/sites/{site_id}/areas returns 403 when not authorized."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Mock valid UUIDs for organization/site that user doesn't have access to
        org_id = "550e8400-e29b-41d4-a716-446655440002"
        site_id = "550e8400-e29b-41d4-a716-446655440003"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        response = await async_client.get(
            f"/api/v1/organizations/{org_id}/sites/{site_id}/areas",
            headers=headers
        )

        # Contract validation - should return 403 when not authorized
        assert response.status_code == 403

        json_data = response.json()

        # Validate error response schema per OpenAPI
        assert "error" in json_data
        assert "code" in json_data
        assert json_data["code"] == "FORBIDDEN"
        assert isinstance(json_data["error"], str)

    @pytest.mark.asyncio
    async def test_areas_get_invalid_uuid_format(self, async_client: AsyncClient):
        """Test that GET /api/v1/organizations/{org_id}/sites/{site_id}/areas returns 422 with invalid UUID format."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Test with invalid org_id format
        response = await async_client.get(
            "/api/v1/organizations/not-a-uuid/sites/550e8400-e29b-41d4-a716-446655440001/areas",
            headers=headers
        )
        assert response.status_code == 422

        # Test with invalid site_id format
        response = await async_client.get(
            "/api/v1/organizations/550e8400-e29b-41d4-a716-446655440000/sites/not-a-uuid/areas",
            headers=headers
        )
        assert response.status_code == 422

    def test_areas_get_content_type(self, client: TestClient):
        """Test that GET /api/v1/organizations/{org_id}/sites/{site_id}/areas returns application/json content-type."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        org_id = "550e8400-e29b-41d4-a716-446655440000"
        site_id = "550e8400-e29b-41d4-a716-446655440001"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        response = client.get(f"/api/v1/organizations/{org_id}/sites/{site_id}/areas", headers=headers)

        # Content-type validation per OpenAPI spec
        assert response.headers.get("content-type") == "application/json"