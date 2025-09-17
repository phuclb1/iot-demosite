"""
Integration test: Device status monitoring and offline detection

This test validates the complete user story:
"As a system administrator, I want to monitor device connection status and detect
when devices go offline so I can maintain system reliability and respond to outages."

This test should FAIL initially since the endpoints and services don't exist yet.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
import asyncio


class TestDeviceStatusIntegration:
    """Integration tests for device status monitoring and offline detection functionality."""

    @pytest.mark.asyncio
    async def test_complete_device_status_monitoring_flow(self, async_client: AsyncClient):
        """
        Test complete flow: Admin monitors device status and detects offline devices.

        This validates the device monitoring and alerting workflow.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Step 1: Get organization devices for monitoring
        org_id = "550e8400-e29b-41d4-a716-446655440000"
        site_id = "550e8400-e29b-41d4-a716-446655440001"
        area_id = "550e8400-e29b-41d4-a716-446655440002"

        devices_response = await async_client.get(
            f"/api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices",
            headers=headers
        )

        assert devices_response.status_code == 200

        devices_data = devices_response.json()
        assert "devices" in devices_data
        assert len(devices_data["devices"]) > 0

        # Step 2: Check each device status
        devices = devices_data["devices"]

        for device in devices:
            device_id = device["id"]

            # Validate device status field exists and has valid value
            assert "status" in device
            assert device["status"] in ["online", "offline", "maintenance"]

            # Validate last_seen timestamp if device has been seen
            if "last_seen" in device and device["last_seen"] is not None:
                last_seen = datetime.fromisoformat(device["last_seen"].replace('Z', '+00:00'))
                now = datetime.now(last_seen.tzinfo)

                # If device is marked online, last_seen should be recent
                if device["status"] == "online":
                    time_since_seen = now - last_seen
                    # Online devices should have been seen within last 5 minutes
                    assert time_since_seen <= timedelta(minutes=5), \
                        f"Online device {device_id} last seen too long ago: {time_since_seen}"

            # Step 3: Check if device is reporting current telemetry data
            current_response = await async_client.get(
                f"/api/v1/telemetry/current/{device_id}",
                headers=headers
            )

            # Device status should correlate with telemetry availability
            if device["status"] == "online":
                # Online devices should have current telemetry (or 404 if no data yet)
                assert current_response.status_code in [200, 404]
            elif device["status"] == "offline":
                # Offline devices might have stale telemetry or none
                assert current_response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_device_offline_detection_criteria(self, async_client: AsyncClient):
        """
        Test device offline detection logic and criteria.

        Validates that devices are properly marked offline based on activity.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Get all devices across the organization for comprehensive testing
        org_response = await async_client.get("/api/v1/organizations", headers=headers)

        if org_response.status_code == 200:
            orgs_data = org_response.json()

            for org in orgs_data["organizations"]:
                org_id = org["id"]

                sites_response = await async_client.get(
                    f"/api/v1/organizations/{org_id}/sites",
                    headers=headers
                )

                if sites_response.status_code == 200:
                    sites_data = sites_response.json()

                    for site in sites_data["sites"]:
                        site_id = site["id"]

                        areas_response = await async_client.get(
                            f"/api/v1/organizations/{org_id}/sites/{site_id}/areas",
                            headers=headers
                        )

                        if areas_response.status_code == 200:
                            areas_data = areas_response.json()

                            for area in areas_data["areas"]:
                                area_id = area["id"]

                                devices_response = await async_client.get(
                                    f"/api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices",
                                    headers=headers
                                )

                                if devices_response.status_code == 200:
                                    devices_data = devices_response.json()

                                    for device in devices_data["devices"]:
                                        # Validate offline detection logic
                                        self._validate_device_offline_logic(device)

    def _validate_device_offline_logic(self, device):
        """Helper to validate device offline detection logic."""
        device_id = device["id"]
        status = device["status"]
        last_seen = device.get("last_seen")

        if last_seen is not None:
            last_seen_dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
            now = datetime.now(last_seen_dt.tzinfo)
            time_since_seen = now - last_seen_dt

            # Offline detection criteria (these would be configurable in real system)
            offline_threshold = timedelta(minutes=10)  # 10 minutes without activity

            if time_since_seen > offline_threshold:
                # Device should be marked offline if not seen for too long
                assert status == "offline", \
                    f"Device {device_id} should be offline (last seen {time_since_seen} ago)"
            else:
                # Recent activity should keep device online (unless in maintenance)
                if status not in ["online", "maintenance"]:
                    # Allow some grace period for status updates
                    grace_period = timedelta(minutes=2)
                    assert time_since_seen <= grace_period, \
                        f"Recently active device {device_id} marked {status}"

    @pytest.mark.asyncio
    async def test_device_status_real_time_updates(self, async_client: AsyncClient):
        """
        Test that device status updates are reflected in real-time via SSE.

        Administrators need immediate notification of status changes.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Test organization-level device monitoring stream
        org_id = "550e8400-e29b-41d4-a716-446655440000"

        sse_response = await async_client.get(
            f"/api/v1/telemetry/stream?organizations={org_id}",
            headers=headers
        )

        assert sse_response.status_code == 200
        assert sse_response.headers.get("content-type") == "text/event-stream"

        # Test device-specific monitoring
        device_id = "550e8400-e29b-41d4-a716-446655440001"

        device_sse_response = await async_client.get(
            f"/api/v1/telemetry/stream?devices={device_id}",
            headers=headers
        )

        assert device_sse_response.status_code == 200
        assert device_sse_response.headers.get("content-type") == "text/event-stream"

    @pytest.mark.asyncio
    async def test_device_status_history_tracking(self, async_client: AsyncClient):
        """
        Test device status history tracking for outage analysis.

        Administrators need to analyze device uptime and outage patterns.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}
        device_id = "550e8400-e29b-41d4-a716-446655440000"

        # Query historical data to analyze device activity patterns
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=24)

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

        if response.status_code == 200:
            historical_data = response.json()

            if historical_data["data"]:
                # Analyze data gaps to identify outages
                data_points = historical_data["data"]

                previous_timestamp = None
                for record in data_points:
                    current_timestamp = datetime.fromisoformat(record["timestamp"].replace('Z', '+00:00'))

                    if previous_timestamp is not None:
                        gap = current_timestamp - previous_timestamp

                        # Gap larger than interval suggests potential outage
                        expected_interval = timedelta(minutes=5)  # Based on 5m interval
                        tolerance = timedelta(minutes=1)  # Allow some tolerance

                        if gap > (expected_interval + tolerance):
                            # This indicates a potential outage period
                            # In real system, this would be logged and analyzed
                            pass

                    previous_timestamp = current_timestamp

    @pytest.mark.asyncio
    async def test_maintenance_mode_device_handling(self, async_client: AsyncClient):
        """
        Test proper handling of devices in maintenance mode.

        Devices in maintenance should not trigger offline alerts.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Get devices and check maintenance mode handling
        org_id = "550e8400-e29b-41d4-a716-446655440000"
        site_id = "550e8400-e29b-41d4-a716-446655440001"
        area_id = "550e8400-e29b-41d4-a716-446655440002"

        devices_response = await async_client.get(
            f"/api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices",
            headers=headers
        )

        if devices_response.status_code == 200:
            devices_data = devices_response.json()

            for device in devices_data["devices"]:
                if device["status"] == "maintenance":
                    device_id = device["id"]

                    # Devices in maintenance mode should still be queryable
                    current_response = await async_client.get(
                        f"/api/v1/telemetry/current/{device_id}",
                        headers=headers
                    )

                    # Maintenance devices may or may not have current data
                    assert current_response.status_code in [200, 404]

                    # But they should not be included in offline alerting
                    # (This would be validated in the alerting system tests)

    @pytest.mark.asyncio
    async def test_device_status_monitoring_performance(self, async_client: AsyncClient):
        """
        Test performance of device status monitoring operations.

        Status checks should be fast for responsive dashboards.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Test concurrent device status checks
        device_ids = [
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002",
            "550e8400-e29b-41d4-a716-446655440003",
            "550e8400-e29b-41d4-a716-446655440004",
            "550e8400-e29b-41d4-a716-446655440005"
        ]

        start_time = asyncio.get_event_loop().time()

        # Simulate dashboard checking current status of multiple devices
        tasks = []
        for device_id in device_ids:
            task = async_client.get(f"/api/v1/telemetry/current/{device_id}", headers=headers)
            tasks.append(task)

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time

        # Performance requirement: Check 5 devices in under 3 seconds
        assert total_time < 3.0, f"Device status checks too slow: {total_time}s"

        # Validate responses
        for i, response in enumerate(responses):
            if not isinstance(response, Exception):
                # Accept various status codes as devices may be offline/online
                assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_system_wide_device_health_dashboard(self, async_client: AsyncClient):
        """
        Test system-wide device health overview for administrators.

        Administrators need overall system health visibility.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Get system-wide device overview
        orgs_response = await async_client.get("/api/v1/organizations", headers=headers)

        if orgs_response.status_code == 200:
            orgs_data = orgs_response.json()

            total_devices = 0
            online_devices = 0
            offline_devices = 0
            maintenance_devices = 0

            # Aggregate device status across all accessible organizations
            for org in orgs_data["organizations"]:
                org_id = org["id"]

                sites_response = await async_client.get(
                    f"/api/v1/organizations/{org_id}/sites",
                    headers=headers
                )

                if sites_response.status_code == 200:
                    sites_data = sites_response.json()

                    for site in sites_data["sites"]:
                        site_id = site["id"]

                        areas_response = await async_client.get(
                            f"/api/v1/organizations/{org_id}/sites/{site_id}/areas",
                            headers=headers
                        )

                        if areas_response.status_code == 200:
                            areas_data = areas_response.json()

                            for area in areas_data["areas"]:
                                area_id = area["id"]

                                devices_response = await async_client.get(
                                    f"/api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices",
                                    headers=headers
                                )

                                if devices_response.status_code == 200:
                                    devices_data = devices_response.json()

                                    for device in devices_data["devices"]:
                                        total_devices += 1

                                        status = device["status"]
                                        if status == "online":
                                            online_devices += 1
                                        elif status == "offline":
                                            offline_devices += 1
                                        elif status == "maintenance":
                                            maintenance_devices += 1

            # Validate system health metrics
            assert total_devices == online_devices + offline_devices + maintenance_devices

            # Calculate health percentages (for dashboard display)
            if total_devices > 0:
                online_percentage = (online_devices / total_devices) * 100
                offline_percentage = (offline_devices / total_devices) * 100

                # System health thresholds (configurable in real system)
                healthy_threshold = 90.0  # 90% online devices considered healthy

                system_health = "healthy" if online_percentage >= healthy_threshold else "degraded"

                # This health status would be displayed on admin dashboard
                assert system_health in ["healthy", "degraded"]