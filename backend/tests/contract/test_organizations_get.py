"""
Contract test for GET /api/v1/organizations endpoint.

This test validates that the endpoint:
- Returns 200 with proper JSON structure when authenticated
- Returns 401 when not authenticated
- Follows the OpenAPI schema specification
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import uuid


class TestOrganizationsGetContract:
    """Contract tests for GET /api/v1/organizations endpoint."""

    @pytest.mark.asyncio
    async def test_organizations_get_success_schema(self, async_client: AsyncClient):
        """Test that GET /api/v1/organizations returns proper schema when authenticated."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Mock authentication header
        headers = {"Authorization": "Bearer mock-jwt-token"}

        response = await async_client.get("/api/v1/organizations", headers=headers)

        # Contract validation - should return 200 with proper JSON structure
        assert response.status_code == 200

        json_data = response.json()

        # Validate response structure per OpenAPI schema
        assert "organizations" in json_data
        assert "total" in json_data
        assert isinstance(json_data["organizations"], list)
        assert isinstance(json_data["total"], int)

        # If organizations exist, validate organization schema
        if json_data["organizations"]:
            org = json_data["organizations"][0]
            required_fields = ["id", "name", "slug", "created_at", "updated_at"]
            for field in required_fields:
                assert field in org

            # Validate UUID format for id
            assert uuid.UUID(org["id"])  # Should not raise ValueError

            # Validate string fields
            assert isinstance(org["name"], str)
            assert isinstance(org["slug"], str)
            assert len(org["name"]) <= 255

            # Validate slug pattern (a-z0-9-)
            import re
            assert re.match(r'^[a-z0-9-]+$', org["slug"])

            # Validate datetime format
            from datetime import datetime
            datetime.fromisoformat(org["created_at"].replace('Z', '+00:00'))
            datetime.fromisoformat(org["updated_at"].replace('Z', '+00:00'))

    @pytest.mark.asyncio
    async def test_organizations_get_unauthorized(self, async_client: AsyncClient):
        """Test that GET /api/v1/organizations returns 401 when not authenticated."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        response = await async_client.get("/api/v1/organizations")

        # Contract validation - should return 401 when no auth header
        assert response.status_code == 401

        json_data = response.json()

        # Validate error response schema per OpenAPI
        assert "error" in json_data
        assert "code" in json_data
        assert json_data["code"] == "UNAUTHORIZED"
        assert isinstance(json_data["error"], str)

    @pytest.mark.asyncio
    async def test_organizations_get_invalid_token(self, async_client: AsyncClient):
        """Test that GET /api/v1/organizations returns 401 with invalid token."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        headers = {"Authorization": "Bearer invalid-token"}
        response = await async_client.get("/api/v1/organizations", headers=headers)

        # Contract validation - should return 401 with invalid token
        assert response.status_code == 401

        json_data = response.json()
        assert "error" in json_data
        assert "code" in json_data
        assert json_data["code"] == "UNAUTHORIZED"

    def test_organizations_get_content_type(self, client: TestClient):
        """Test that GET /api/v1/organizations returns application/json content-type."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}
        response = client.get("/api/v1/organizations", headers=headers)

        # Content-type validation per OpenAPI spec
        assert response.headers.get("content-type") == "application/json"