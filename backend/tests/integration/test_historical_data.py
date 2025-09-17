"""
Integration test: Historical data time range selection

This test validates the complete user story:
"As a user, I want to select custom time ranges and view historical telemetry data
with different aggregation intervals so I can analyze trends and investigate past incidents."

This test should FAIL initially since the endpoints and services don't exist yet.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
import asyncio


class TestHistoricalDataIntegration:
    """Integration tests for historical data time range selection functionality."""

    @pytest.mark.asyncio
    async def test_complete_historical_data_query_flow(self, async_client: AsyncClient):
        """
        Test complete flow: User selects time range and views historical data with aggregation.

        This validates the typical historical analysis workflow.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}
        device_id = "550e8400-e29b-41d4-a716-446655440000"

        # Test Case 1: Last 24 hours with 1-hour intervals (typical dashboard view)
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)

        params = {
            "start": start_time.isoformat() + "Z",
            "end": end_time.isoformat() + "Z",
            "interval": "1h"
        }

        response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params=params
        )

        assert response.status_code == 200

        data = response.json()

        # Validate response structure
        assert "data" in data
        assert "total" in data
        assert "interval" in data
        assert data["interval"] == "1h"

        # Validate data points are within requested time range
        if data["data"]:
            for record in data["data"]:
                timestamp = datetime.fromisoformat(record["timestamp"].replace('Z', '+00:00'))
                assert start_time <= timestamp <= end_time

        # Test Case 2: Last week with daily aggregation (trend analysis)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=7)

        params = {
            "start": start_time.isoformat() + "Z",
            "end": end_time.isoformat() + "Z",
            "interval": "1h"  # Daily would be ideal but not in enum, using 1h
        }

        response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params=params
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_all_supported_aggregation_intervals(self, async_client: AsyncClient):
        """
        Test all supported aggregation intervals per OpenAPI spec.

        Validates: [1s, 5s, 30s, 1m, 5m, 1h]
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}
        device_id = "550e8400-e29b-41d4-a716-446655440000"

        # Use a smaller time range for testing different intervals
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)

        supported_intervals = ["1s", "5s", "30s", "1m", "5m", "1h"]

        for interval in supported_intervals:
            params = {
                "start": start_time.isoformat() + "Z",
                "end": end_time.isoformat() + "Z",
                "interval": interval
            }

            response = await async_client.get(
                f"/api/v1/telemetry/historical/{device_id}",
                headers=headers,
                params=params
            )

            assert response.status_code == 200, f"Failed for interval: {interval}"

            data = response.json()
            assert data["interval"] == interval, f"Interval mismatch for {interval}"

            # Validate data consistency
            assert "data" in data
            assert "total" in data
            assert isinstance(data["total"], int)

    @pytest.mark.asyncio
    async def test_default_interval_behavior(self, async_client: AsyncClient):
        """
        Test default interval behavior when not specified.

        Per OpenAPI spec, default should be "1s".
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}
        device_id = "550e8400-e29b-41d4-a716-446655440000"

        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=10)

        params = {
            "start": start_time.isoformat() + "Z",
            "end": end_time.isoformat() + "Z"
            # No interval specified - should default to "1s"
        }

        response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params=params
        )

        assert response.status_code == 200

        data = response.json()
        assert data["interval"] == "1s", "Default interval should be 1s"

    @pytest.mark.asyncio
    async def test_time_range_validation_edge_cases(self, async_client: AsyncClient):
        """
        Test edge cases for time range validation.

        Validates proper handling of invalid time ranges.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}
        device_id = "550e8400-e29b-41d4-a716-446655440000"

        # Test Case 1: Start time after end time (invalid)
        end_time = datetime.now()
        start_time = end_time + timedelta(hours=1)  # Future start time

        params = {
            "start": start_time.isoformat() + "Z",
            "end": end_time.isoformat() + "Z",
            "interval": "5m"
        }

        response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params=params
        )

        assert response.status_code == 422, "Should reject start > end"

        # Test Case 2: Very large time range (should handle gracefully)
        end_time = datetime.now()
        start_time = end_time - timedelta(days=365)  # 1 year

        params = {
            "start": start_time.isoformat() + "Z",
            "end": end_time.isoformat() + "Z",
            "interval": "1h"
        }

        response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params=params
        )

        # Should either succeed or return appropriate error (not crash)
        assert response.status_code in [200, 400, 422]

        # Test Case 3: Future time range (no data expected)
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=1)

        params = {
            "start": start_time.isoformat() + "Z",
            "end": end_time.isoformat() + "Z",
            "interval": "5m"
        }

        response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params=params
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0, "Future time range should return no data"

    @pytest.mark.asyncio
    async def test_historical_data_performance_requirements(self, async_client: AsyncClient):
        """
        Test performance requirements for historical data queries.

        Users expect responsive queries for dashboard interactions.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}
        device_id = "550e8400-e29b-41d4-a716-446655440000"

        # Test performance for different query sizes
        test_cases = [
            {"duration": timedelta(hours=1), "interval": "1m", "max_time": 2.0},
            {"duration": timedelta(hours=6), "interval": "5m", "max_time": 3.0},
            {"duration": timedelta(hours=24), "interval": "1h", "max_time": 5.0},
        ]

        for case in test_cases:
            end_time = datetime.now()
            start_time = end_time - case["duration"]

            params = {
                "start": start_time.isoformat() + "Z",
                "end": end_time.isoformat() + "Z",
                "interval": case["interval"]
            }

            start_request = asyncio.get_event_loop().time()

            response = await async_client.get(
                f"/api/v1/telemetry/historical/{device_id}",
                headers=headers,
                params=params
            )

            end_request = asyncio.get_event_loop().time()
            request_time = end_request - start_request

            assert response.status_code == 200
            assert request_time < case["max_time"], \
                f"Query too slow: {request_time}s > {case['max_time']}s for {case['duration']}"

    @pytest.mark.asyncio
    async def test_historical_data_aggregation_accuracy(self, async_client: AsyncClient):
        """
        Test that aggregation intervals produce consistent data.

        Validates that aggregated data maintains proper temporal relationships.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}
        device_id = "550e8400-e29b-41d4-a716-446655440000"

        # Query same time range with different intervals
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=2)

        # Get high-resolution data
        params_high_res = {
            "start": start_time.isoformat() + "Z",
            "end": end_time.isoformat() + "Z",
            "interval": "1m"
        }

        high_res_response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params=params_high_res
        )

        # Get low-resolution data
        params_low_res = {
            "start": start_time.isoformat() + "Z",
            "end": end_time.isoformat() + "Z",
            "interval": "5m"
        }

        low_res_response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params=params_low_res
        )

        assert high_res_response.status_code == 200
        assert low_res_response.status_code == 200

        high_res_data = high_res_response.json()
        low_res_data = low_res_response.json()

        # Validate aggregation consistency
        if high_res_data["data"] and low_res_data["data"]:
            # Higher resolution should have more or equal data points
            assert len(high_res_data["data"]) >= len(low_res_data["data"])

            # All timestamps should be within the requested range
            for record in high_res_data["data"]:
                timestamp = datetime.fromisoformat(record["timestamp"].replace('Z', '+00:00'))
                assert start_time <= timestamp <= end_time

            for record in low_res_data["data"]:
                timestamp = datetime.fromisoformat(record["timestamp"].replace('Z', '+00:00'))
                assert start_time <= timestamp <= end_time

    @pytest.mark.asyncio
    async def test_multiple_device_historical_analysis(self, async_client: AsyncClient):
        """
        Test historical data analysis across multiple devices.

        Users often need to compare historical data from multiple devices.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}

        device_ids = [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
            "550e8400-e29b-41d4-a716-446655440003"
        ]

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=6)

        params = {
            "start": start_time.isoformat() + "Z",
            "end": end_time.isoformat() + "Z",
            "interval": "1h"
        }

        # Query historical data for multiple devices concurrently
        tasks = []
        for device_id in device_ids:
            task = async_client.get(
                f"/api/v1/telemetry/historical/{device_id}",
                headers=headers,
                params=params
            )
            tasks.append(task)

        start_time_query = asyncio.get_event_loop().time()
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time_query = asyncio.get_event_loop().time()

        query_time = end_time_query - start_time_query

        # Performance requirement: Multiple device queries under 5 seconds
        assert query_time < 5.0, f"Multi-device query too slow: {query_time}s"

        # Validate all responses
        for i, response in enumerate(responses):
            if not isinstance(response, Exception):
                assert response.status_code == 200, f"Device {device_ids[i]} query failed"

                data = response.json()
                assert "data" in data
                assert "interval" in data
                assert data["interval"] == "1h"

    @pytest.mark.asyncio
    async def test_historical_data_incident_investigation_scenario(self, async_client: AsyncClient):
        """
        Test scenario: User investigates past incident using historical data.

        This simulates a real-world incident investigation workflow.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}
        device_id = "550e8400-e29b-41d4-a716-446655440000"

        # Scenario: Investigate what happened yesterday between 2-4 PM
        yesterday = datetime.now() - timedelta(days=1)
        incident_start = yesterday.replace(hour=14, minute=0, second=0, microsecond=0)
        incident_end = yesterday.replace(hour=16, minute=0, second=0, microsecond=0)

        # Step 1: Get overview with 5-minute resolution
        overview_params = {
            "start": incident_start.isoformat() + "Z",
            "end": incident_end.isoformat() + "Z",
            "interval": "5m"
        }

        overview_response = await async_client.get(
            f"/api/v1/telemetry/historical/{device_id}",
            headers=headers,
            params=overview_params
        )

        assert overview_response.status_code == 200
        overview_data = overview_response.json()

        # Step 2: If anomalies found, drill down with 30-second resolution
        if overview_data["data"]:
            # Simulate finding anomaly and drilling down to specific 10-minute window
            anomaly_start = incident_start + timedelta(minutes=30)
            anomaly_end = anomaly_start + timedelta(minutes=10)

            detail_params = {
                "start": anomaly_start.isoformat() + "Z",
                "end": anomaly_end.isoformat() + "Z",
                "interval": "30s"
            }

            detail_response = await async_client.get(
                f"/api/v1/telemetry/historical/{device_id}",
                headers=headers,
                params=detail_params
            )

            assert detail_response.status_code == 200
            detail_data = detail_response.json()

            # Validate detailed data structure
            assert detail_data["interval"] == "30s"
            assert "data" in detail_data

            if detail_data["data"]:
                # Validate high-resolution data has required fields for analysis
                sample_record = detail_data["data"][0]
                analysis_fields = ["vibration", "temperature", "power", "electricity", "timestamp"]
                for field in analysis_fields:
                    assert field in sample_record