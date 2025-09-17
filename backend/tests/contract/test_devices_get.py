"""
Contract test for GET /api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices endpoint.

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


class TestDevicesGetContract:
    """Contract tests for GET /api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices endpoint."""

    @pytest.mark.asyncio
    async def test_devices_get_success_schema(self, async_client: AsyncClient):
        """Test that GET /api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices returns proper schema when authenticated."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Mock valid UUIDs for path parameters
        org_id = "550e8400-e29b-41d4-a716-446655440000"
        site_id = "550e8400-e29b-41d4-a716-446655440001"
        area_id = "550e8400-e29b-41d4-a716-446655440002"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        response = await async_client.get(
            f"/api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices",
            headers=headers
        )

        # Contract validation - should return 200 with proper JSON structure
        assert response.status_code == 200

        json_data = response.json()

        # Validate response structure per OpenAPI schema
        assert "devices" in json_data
        assert isinstance(json_data["devices"], list)

        # If devices exist, validate device schema
        if json_data["devices"]:
            device = json_data["devices"][0]
            required_fields = ["id", "area_id", "name", "model", "status", "created_at", "updated_at"]
            for field in required_fields:
                assert field in device

            # Validate UUID format for id and area_id
            assert uuid.UUID(device["id"])  # Should not raise ValueError
            assert uuid.UUID(device["area_id"])  # Should not raise ValueError

            # Validate string fields
            assert isinstance(device["name"], str)
            assert isinstance(device["model"], str)
            assert len(device["name"]) <= 255
            assert len(device["model"]) <= 255

            # Validate status enum
            valid_statuses = ["online", "offline", "maintenance"]
            assert device["status"] in valid_statuses

            # Validate datetime format
            from datetime import datetime
            datetime.fromisoformat(device["created_at"].replace('Z', '+00:00'))
            datetime.fromisoformat(device["updated_at"].replace('Z', '+00:00'))

            # Validate area_id matches the path parameter
            assert device["area_id"] == area_id

            # Validate optional fields if present
            if "firmware_version" in device and device["firmware_version"] is not None:
                assert isinstance(device["firmware_version"], str)

            if "mac_address" in device and device["mac_address"] is not None:
                assert isinstance(device["mac_address"], str)
                # Validate MAC address pattern
                import re
                assert re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', device["mac_address"])

            if "last_seen" in device and device["last_seen"] is not None:
                datetime.fromisoformat(device["last_seen"].replace('Z', '+00:00'))

    @pytest.mark.asyncio
    async def test_devices_get_unauthorized(self, async_client: AsyncClient):
        """Test that GET /api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices returns 401 when not authenticated."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        org_id = "550e8400-e29b-41d4-a716-446655440000"
        site_id = "550e8400-e29b-41d4-a716-446655440001"
        area_id = "550e8400-e29b-41d4-a716-446655440002"

        response = await async_client.get(
            f"/api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices"
        )

        # Contract validation - should return 401 when no auth header
        assert response.status_code == 401

        json_data = response.json()

        # Validate error response schema per OpenAPI
        assert "error" in json_data
        assert "code" in json_data
        assert json_data["code"] == "UNAUTHORIZED"
        assert isinstance(json_data["error"], str)

    @pytest.mark.asyncio
    async def test_devices_get_forbidden(self, async_client: AsyncClient):
        """Test that GET /api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices returns 403 when not authorized."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Mock valid UUIDs for organization/site/area that user doesn't have access to
        org_id = "550e8400-e29b-41d4-a716-446655440003"
        site_id = "550e8400-e29b-41d4-a716-446655440004"
        area_id = "550e8400-e29b-41d4-a716-446655440005"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        response = await async_client.get(
            f"/api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices",
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
    async def test_devices_get_invalid_uuid_format(self, async_client: AsyncClient):
        """Test that GET /api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices returns 422 with invalid UUID format."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Test with invalid org_id format
        response = await async_client.get(
            "/api/v1/organizations/not-a-uuid/sites/550e8400-e29b-41d4-a716-446655440001/areas/550e8400-e29b-41d4-a716-446655440002/devices",
            headers=headers
        )
        assert response.status_code == 422

        # Test with invalid site_id format
        response = await async_client.get(
            "/api/v1/organizations/550e8400-e29b-41d4-a716-446655440000/sites/not-a-uuid/areas/550e8400-e29b-41d4-a716-446655440002/devices",
            headers=headers
        )
        assert response.status_code == 422

        # Test with invalid area_id format
        response = await async_client.get(
            "/api/v1/organizations/550e8400-e29b-41d4-a716-446655440000/sites/550e8400-e29b-41d4-a716-446655440001/areas/not-a-uuid/devices",
            headers=headers
        )
        assert response.status_code == 422

    def test_devices_get_content_type(self, client: TestClient):
        """Test that GET /api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices returns application/json content-type."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        org_id = "550e8400-e29b-41d4-a716-446655440000"
        site_id = "550e8400-e29b-41d4-a716-446655440001"
        area_id = "550e8400-e29b-41d4-a716-446655440002"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        response = client.get(
            f"/api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices",
            headers=headers
        )

        # Content-type validation per OpenAPI spec
        assert response.headers.get("content-type") == "application/json"