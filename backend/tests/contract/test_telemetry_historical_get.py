"""
Contract test for GET /api/v1/telemetry/historical/{device_id} endpoint.

This test validates that the endpoint:
- Returns 200 with proper JSON structure when authenticated with required query parameters
- Returns 401 when not authenticated
- Returns 422 when required query parameters are missing
- Validates UUID format for path parameters
- Validates datetime format for query parameters
- Follows the OpenAPI schema specification
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import uuid


class TestTelemetryHistoricalGetContract:
    """Contract tests for GET /api/v1/telemetry/historical/{device_id} endpoint."""

    @pytest.mark.asyncio
    async def test_telemetry_historical_get_success_schema(self, async_client: AsyncClient):
        """Test that GET /api/v1/telemetry/historical/{device_id} returns proper schema when authenticated."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Mock valid UUID for device ID
        device_id = "550e8400-e29b-41d4-a716-446655440000"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Required query parameters per OpenAPI spec
        params = {
            "start": "2025-09-12T00:00:00Z",
            "end": "2025-09-12T23:59:59Z",
            "interval": "1m"  # Optional, testing with value
        }

        response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params=params
        )

        # Contract validation - should return 200 with proper JSON structure
        assert response.status_code == 200

        json_data = response.json()

        # Validate response structure per OpenAPI schema
        required_fields = ["data", "total", "interval"]
        for field in required_fields:
            assert field in json_data

        # Validate data array structure
        assert isinstance(json_data["data"], list)
        assert isinstance(json_data["total"], int)
        assert isinstance(json_data["interval"], str)

        # Validate interval matches request
        assert json_data["interval"] == "1m"

        # If data exists, validate TelemetryReading schema
        if json_data["data"]:
            reading = json_data["data"][0]
            required_reading_fields = [
                "device_id", "vibration", "temperature", "power",
                "electricity", "timestamp", "org", "site", "area"
            ]
            for field in required_reading_fields:
                assert field in reading

            # Validate UUID format for device_id
            assert uuid.UUID(reading["device_id"])  # Should not raise ValueError
            assert reading["device_id"] == device_id

            # Validate numeric fields (floats)
            assert isinstance(reading["vibration"], (int, float))
            assert isinstance(reading["temperature"], (int, float))
            assert isinstance(reading["power"], (int, float))
            assert isinstance(reading["electricity"], (int, float))

            # Validate timestamp format and range
            from datetime import datetime
            timestamp = datetime.fromisoformat(reading["timestamp"].replace('Z', '+00:00'))
            start_time = datetime.fromisoformat(params["start"].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(params["end"].replace('Z', '+00:00'))
            assert start_time <= timestamp <= end_time

            # Validate string fields
            assert isinstance(reading["org"], str)
            assert isinstance(reading["site"], str)
            assert isinstance(reading["area"], str)

    @pytest.mark.asyncio
    async def test_telemetry_historical_get_default_interval(self, async_client: AsyncClient):
        """Test that GET /api/v1/telemetry/historical/{device_id} uses default interval when not specified."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        device_id = "550e8400-e29b-41d4-a716-446655440000"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Only required parameters, no interval
        params = {
            "start": "2025-09-12T00:00:00Z",
            "end": "2025-09-12T23:59:59Z"
        }

        response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params=params
        )

        assert response.status_code == 200
        json_data = response.json()

        # Should use default interval of "1s" per OpenAPI spec
        assert json_data["interval"] == "1s"

    @pytest.mark.asyncio
    async def test_telemetry_historical_get_unauthorized(self, async_client: AsyncClient):
        """Test that GET /api/v1/telemetry/historical/{device_id} returns 401 when not authenticated."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        device_id = "550e8400-e29b-41d4-a716-446655440000"
        params = {
            "start": "2025-09-12T00:00:00Z",
            "end": "2025-09-12T23:59:59Z"
        }

        response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            params=params
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
    async def test_telemetry_historical_get_missing_required_params(self, async_client: AsyncClient):
        """Test that GET /api/v1/telemetry/historical/{device_id} returns 422 when required params are missing."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        device_id = "550e8400-e29b-41d4-a716-446655440000"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Missing start parameter
        response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params={"end": "2025-09-12T23:59:59Z"}
        )
        assert response.status_code == 422

        # Missing end parameter
        response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params={"start": "2025-09-12T00:00:00Z"}
        )
        assert response.status_code == 422

        # Missing both required parameters
        response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_telemetry_historical_get_invalid_interval(self, async_client: AsyncClient):
        """Test that GET /api/v1/telemetry/historical/{device_id} returns 422 with invalid interval."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        device_id = "550e8400-e29b-41d4-a716-446655440000"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Invalid interval value (not in enum: [1s, 5s, 30s, 1m, 5m, 1h])
        params = {
            "start": "2025-09-12T00:00:00Z",
            "end": "2025-09-12T23:59:59Z",
            "interval": "10s"  # Invalid value
        }

        response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params=params
        )

        # Contract validation - should return 422 for invalid enum value
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_telemetry_historical_get_invalid_datetime_format(self, async_client: AsyncClient):
        """Test that GET /api/v1/telemetry/historical/{device_id} returns 422 with invalid datetime format."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        device_id = "550e8400-e29b-41d4-a716-446655440000"
        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Invalid datetime format
        params = {
            "start": "2025-09-12",  # Should be ISO 8601 with time
            "end": "2025-09-12T23:59:59Z"
        }

        response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params=params
        )

        # Contract validation - should return 422 for invalid datetime format
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_telemetry_historical_get_invalid_device_id_format(self, async_client: AsyncClient):
        """Test that GET /api/v1/telemetry/historical/{device_id} returns 422 with invalid UUID format."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}
        invalid_device_id = "not-a-uuid"
        params = {
            "start": "2025-09-12T00:00:00Z",
            "end": "2025-09-12T23:59:59Z"
        }

        response = await async_client.get(
            f"/api/v1/telemetry/historical/{invalid_device_id}",
            headers=headers,
            params=params
        )

        # Contract validation - should return 422 for invalid UUID format
        assert response.status_code == 422

    def test_telemetry_historical_get_content_type(self, client: TestClient):
        """Test that GET /api/v1/telemetry/historical/{device_id} returns application/json content-type."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        device_id = "550e8400-e29b-41d4-a716-446655440000"
        headers = {"Authorization": "Bearer mock-jwt-token"}
        params = {
            "start": "2025-09-12T00:00:00Z",
            "end": "2025-09-12T23:59:59Z"
        }

        response = client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params=params
        )

        # Content-type validation per OpenAPI spec
        assert response.headers.get("content-type") == "application/json"