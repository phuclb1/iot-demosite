"""
Contract test for GET /api/v1/telemetry/current/{device_id} endpoint.

This test validates that the endpoint:
- Returns 200 with proper JSON structure when authenticated and device exists
- Returns 401 when not authenticated
- Returns 404 when device not found or no telemetry data available
- Validates UUID format for path parameters
- Follows the OpenAPI schema specification
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import uuid


class TestTelemetryCurrentGetContract:
    """Contract tests for GET /api/v1/telemetry/current/{device_id} endpoint."""

    @pytest.mark.asyncio
    async def test_telemetry_current_get_success_schema(self, async_client: AsyncClient):
        """Test that GET /api/v1/telemetry/current/{device_id} returns proper schema when authenticated."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Mock valid UUID for device ID
        device_id = "550e8400-e29b-41d4-a716-446655440000"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        response = await async_client.get(f"/api/v1/telemetry/current/{device_id}", headers=headers)

        # Contract validation - should return 200 with proper JSON structure
        assert response.status_code == 200

        json_data = response.json()

        # Validate response structure per OpenAPI schema (TelemetryReading)
        required_fields = [
            "device_id", "vibration", "temperature", "power",
            "electricity", "timestamp", "org", "site", "area"
        ]
        for field in required_fields:
            assert field in json_data

        # Validate UUID format for device_id
        assert uuid.UUID(json_data["device_id"])  # Should not raise ValueError
        assert json_data["device_id"] == device_id

        # Validate numeric fields (floats)
        assert isinstance(json_data["vibration"], (int, float))
        assert isinstance(json_data["temperature"], (int, float))
        assert isinstance(json_data["power"], (int, float))
        assert isinstance(json_data["electricity"], (int, float))

        # Validate timestamp format
        from datetime import datetime
        datetime.fromisoformat(json_data["timestamp"].replace('Z', '+00:00'))

        # Validate string fields
        assert isinstance(json_data["org"], str)
        assert isinstance(json_data["site"], str)
        assert isinstance(json_data["area"], str)

    @pytest.mark.asyncio
    async def test_telemetry_current_get_unauthorized(self, async_client: AsyncClient):
        """Test that GET /api/v1/telemetry/current/{device_id} returns 401 when not authenticated."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        device_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.get(f"/api/v1/telemetry/current/{device_id}")

        # Contract validation - should return 401 when no auth header
        assert response.status_code == 401

        json_data = response.json()

        # Validate error response schema per OpenAPI
        assert "error" in json_data
        assert "code" in json_data
        assert json_data["code"] == "UNAUTHORIZED"
        assert isinstance(json_data["error"], str)

    @pytest.mark.asyncio
    async def test_telemetry_current_get_not_found(self, async_client: AsyncClient):
        """Test that GET /api/v1/telemetry/current/{device_id} returns 404 when device not found or no data."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Mock UUID for non-existent device
        device_id = "550e8400-e29b-41d4-a716-446655440999"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        response = await async_client.get(f"/api/v1/telemetry/current/{device_id}", headers=headers)

        # Contract validation - should return 404 when device not found or no telemetry data
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_telemetry_current_get_invalid_device_id_format(self, async_client: AsyncClient):
        """Test that GET /api/v1/telemetry/current/{device_id} returns 422 with invalid UUID format."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}
        invalid_device_id = "not-a-uuid"

        response = await async_client.get(f"/api/v1/telemetry/current/{invalid_device_id}", headers=headers)

        # Contract validation - should return 422 for invalid UUID format
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_telemetry_current_get_invalid_token(self, async_client: AsyncClient):
        """Test that GET /api/v1/telemetry/current/{device_id} returns 401 with invalid token."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        device_id = "550e8400-e29b-41d4-a716-446655440000"
        headers = {"Authorization": "Bearer invalid-token"}

        response = await async_client.get(f"/api/v1/telemetry/current/{device_id}", headers=headers)

        # Contract validation - should return 401 with invalid token
        assert response.status_code == 401

        json_data = response.json()
        assert "error" in json_data
        assert "code" in json_data
        assert json_data["code"] == "UNAUTHORIZED"

    def test_telemetry_current_get_content_type(self, client: TestClient):
        """Test that GET /api/v1/telemetry/current/{device_id} returns application/json content-type."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        device_id = "550e8400-e29b-41d4-a716-446655440000"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        response = client.get(f"/api/v1/telemetry/current/{device_id}", headers=headers)

        # Content-type validation per OpenAPI spec
        assert response.headers.get("content-type") == "application/json"