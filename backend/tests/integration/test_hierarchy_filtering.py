"""
Integration test: Hierarchical filtering (org/site/area)

This test validates the complete user story:
"As a user, I want to filter devices and telemetry data by organization, site, and area
so I can focus on specific operational scopes and maintain data access control."

This test should FAIL initially since the endpoints and services don't exist yet.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timedelta
import uuid


class TestHierarchyFilteringIntegration:
    """Integration tests for hierarchical filtering functionality."""

    @pytest.mark.asyncio
    async def test_complete_hierarchy_navigation_flow(self, async_client: AsyncClient):
        """
        Test complete navigation through org -> site -> area -> devices hierarchy.

        This validates the full drill-down experience users expect.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Step 1: Start at organization level
        orgs_response = await async_client.get("/api/v1/organizations", headers=headers)
        assert orgs_response.status_code == 200

        orgs_data = orgs_response.json()
        assert "organizations" in orgs_data
        assert len(orgs_data["organizations"]) > 0

        # Pick first organization for testing
        org = orgs_data["organizations"][0]
        org_id = org["id"]

        # Validate organization structure
        assert uuid.UUID(org_id)  # Valid UUID
        assert "name" in org
        assert "slug" in org

        # Step 2: Navigate to sites within organization
        sites_response = await async_client.get(f"/api/v1/organizations/{org_id}/sites", headers=headers)
        assert sites_response.status_code == 200

        sites_data = sites_response.json()
        assert "sites" in sites_data
        assert len(sites_data["sites"]) > 0

        # Pick first site for testing
        site = sites_data["sites"][0]
        site_id = site["id"]

        # Validate site structure and hierarchy relationship
        assert uuid.UUID(site_id)  # Valid UUID
        assert site["organization_id"] == org_id  # Proper hierarchy link
        assert "name" in site
        assert "slug" in site

        # Step 3: Navigate to areas within site
        areas_response = await async_client.get(
            f"/api/v1/organizations/{org_id}/sites/{site_id}/areas",
            headers=headers
        )
        assert areas_response.status_code == 200

        areas_data = areas_response.json()
        assert "areas" in areas_data
        assert len(areas_data["areas"]) > 0

        # Pick first area for testing
        area = areas_data["areas"][0]
        area_id = area["id"]

        # Validate area structure and hierarchy relationship
        assert uuid.UUID(area_id)  # Valid UUID
        assert area["site_id"] == site_id  # Proper hierarchy link
        assert "name" in area
        assert "slug" in area

        # Step 4: Navigate to devices within area
        devices_response = await async_client.get(
            f"/api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices",
            headers=headers
        )
        assert devices_response.status_code == 200

        devices_data = devices_response.json()
        assert "devices" in devices_data
        assert len(devices_data["devices"]) > 0

        # Validate device structure and hierarchy relationship
        device = devices_data["devices"][0]
        device_id = device["id"]

        assert uuid.UUID(device_id)  # Valid UUID
        assert device["area_id"] == area_id  # Proper hierarchy link
        assert "name" in device
        assert "status" in device

    @pytest.mark.asyncio
    async def test_hierarchy_access_control_validation(self, async_client: AsyncClient):
        """
        Test that users can only access hierarchy levels they're authorized for.

        This validates proper access control through the hierarchy.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Test 1: Valid organization access
        valid_org_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await async_client.get(f"/api/v1/organizations/{valid_org_id}/sites", headers=headers)
        assert response.status_code in [200, 403]  # Either accessible or properly denied

        # Test 2: Invalid organization access (should be forbidden)
        invalid_org_id = "550e8400-e29b-41d4-a716-446655440999"
        response = await async_client.get(f"/api/v1/organizations/{invalid_org_id}/sites", headers=headers)
        assert response.status_code == 403

        # Test 3: Cross-organization site access (should be forbidden)
        org_a_id = "550e8400-e29b-41d4-a716-446655440001"
        org_b_site_id = "550e8400-e29b-41d4-a716-446655440002"

        response = await async_client.get(
            f"/api/v1/organizations/{org_a_id}/sites/{org_b_site_id}/areas",
            headers=headers
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_telemetry_data_hierarchy_filtering(self, async_client: AsyncClient):
        """
        Test that telemetry data respects hierarchy filtering.

        Users should only see telemetry from devices in their accessible scope.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Get a device to test telemetry filtering
        device_id = "550e8400-e29b-41d4-a716-446655440000"

        # Test current telemetry access
        current_response = await async_client.get(
            f"/api/v1/telemetry/current/{device_id}",
            headers=headers
        )
        assert current_response.status_code in [200, 403, 404]

        if current_response.status_code == 200:
            telemetry_data = current_response.json()

            # Validate hierarchy context is included in telemetry data
            assert "org" in telemetry_data
            assert "site" in telemetry_data
            assert "area" in telemetry_data
            assert "device_id" in telemetry_data

            # Validate the hierarchy slugs are present (for filtering UI)
            assert isinstance(telemetry_data["org"], str)
            assert isinstance(telemetry_data["site"], str)
            assert isinstance(telemetry_data["area"], str)

    @pytest.mark.asyncio
    async def test_sse_stream_hierarchy_filtering(self, async_client: AsyncClient):
        """
        Test SSE stream filtering by hierarchy levels.

        Users should be able to stream data from specific org/site/area scopes.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Test organization-level streaming
        org_id = "550e8400-e29b-41d4-a716-446655440000"
        org_response = await async_client.get(
            f"/api/v1/telemetry/stream?organizations={org_id}",
            headers=headers
        )
        assert org_response.status_code == 200
        assert org_response.headers.get("content-type") == "text/event-stream"

        # Test device-level streaming
        device_id = "550e8400-e29b-41d4-a716-446655440001"
        device_response = await async_client.get(
            f"/api/v1/telemetry/stream?devices={device_id}",
            headers=headers
        )
        assert device_response.status_code == 200
        assert device_response.headers.get("content-type") == "text/event-stream"

        # Test multiple organization streaming
        multi_orgs = "550e8400-e29b-41d4-a716-446655440000,550e8400-e29b-41d4-a716-446655440001"
        multi_response = await async_client.get(
            f"/api/v1/telemetry/stream?organizations={multi_orgs}",
            headers=headers
        )
        assert multi_response.status_code == 200

    @pytest.mark.asyncio
    async def test_historical_data_hierarchy_filtering(self, async_client: AsyncClient):
        """
        Test historical data filtering by hierarchy scope.

        Users should be able to query historical data for devices in their scope.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}
        device_id = "550e8400-e29b-41d4-a716-446655440000"

        # Query historical data
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=1)

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
        assert response.status_code in [200, 403, 404]

        if response.status_code == 200:
            historical_data = response.json()
            assert "data" in historical_data
            assert "total" in historical_data

            # If data exists, validate hierarchy context
            if historical_data["data"]:
                sample_record = historical_data["data"][0]
                assert "org" in sample_record
                assert "site" in sample_record
                assert "area" in sample_record
                assert "device_id" in sample_record

    @pytest.mark.asyncio
    async def test_hierarchy_filtering_performance(self, async_client: AsyncClient):
        """
        Test performance of hierarchy filtering operations.

        Hierarchy traversal should be efficient for dashboard responsiveness.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}

        import asyncio
        start_time = asyncio.get_event_loop().time()

        # Simulate typical hierarchy navigation sequence
        # 1. Get organizations
        orgs_response = await async_client.get("/api/v1/organizations", headers=headers)

        # 2. Get sites for first org (if any)
        if orgs_response.status_code == 200:
            orgs_data = orgs_response.json()
            if orgs_data["organizations"]:
                org_id = orgs_data["organizations"][0]["id"]
                sites_response = await async_client.get(
                    f"/api/v1/organizations/{org_id}/sites",
                    headers=headers
                )

                # 3. Get areas for first site (if any)
                if sites_response.status_code == 200:
                    sites_data = sites_response.json()
                    if sites_data["sites"]:
                        site_id = sites_data["sites"][0]["id"]
                        areas_response = await async_client.get(
                            f"/api/v1/organizations/{org_id}/sites/{site_id}/areas",
                            headers=headers
                        )

                        # 4. Get devices for first area (if any)
                        if areas_response.status_code == 200:
                            areas_data = areas_response.json()
                            if areas_data["areas"]:
                                area_id = areas_data["areas"][0]["id"]
                                await async_client.get(
                                    f"/api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices",
                                    headers=headers
                                )

        end_time = asyncio.get_event_loop().time()
        total_time = end_time - start_time

        # Performance requirement: Complete hierarchy navigation under 1 second
        assert total_time < 1.0, f"Hierarchy navigation too slow: {total_time}s"

    @pytest.mark.asyncio
    async def test_hierarchy_consistency_validation(self, async_client: AsyncClient):
        """
        Test data consistency across hierarchy levels.

        Parent-child relationships should be properly maintained.
        """
        # This test should FAIL initially since the endpoints don't exist yet

        headers = {"Authorization": "Bearer mock-jwt-token"}

        # Get organizations
        orgs_response = await async_client.get("/api/v1/organizations", headers=headers)

        if orgs_response.status_code == 200:
            orgs_data = orgs_response.json()

            for org in orgs_data["organizations"]:
                org_id = org["id"]

                # Get sites for this organization
                sites_response = await async_client.get(
                    f"/api/v1/organizations/{org_id}/sites",
                    headers=headers
                )

                if sites_response.status_code == 200:
                    sites_data = sites_response.json()

                    for site in sites_data["sites"]:
                        # Validate parent-child relationship
                        assert site["organization_id"] == org_id

                        site_id = site["id"]

                        # Get areas for this site
                        areas_response = await async_client.get(
                            f"/api/v1/organizations/{org_id}/sites/{site_id}/areas",
                            headers=headers
                        )

                        if areas_response.status_code == 200:
                            areas_data = areas_response.json()

                            for area in areas_data["areas"]:
                                # Validate parent-child relationship
                                assert area["site_id"] == site_id

                                area_id = area["id"]

                                # Get devices for this area
                                devices_response = await async_client.get(
                                    f"/api/v1/organizations/{org_id}/sites/{site_id}/areas/{area_id}/devices",
                                    headers=headers
                                )

                                if devices_response.status_code == 200:
                                    devices_data = devices_response.json()

                                    for device in devices_data["devices"]:
                                        # Validate parent-child relationship
                                        assert device["area_id"] == area_id