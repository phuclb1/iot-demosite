"""
Contract test for POST /api/v1/auth/login endpoint.

This test validates that the endpoint:
- Returns 200 with proper JSON structure and JWT token when credentials are valid
- Returns 401 when credentials are invalid
- Returns 422 when request body is malformed or missing required fields
- Validates email format and password minimum length
- Follows the OpenAPI schema specification
"""

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
import uuid


class TestAuthLoginPostContract:
    """Contract tests for POST /api/v1/auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_auth_login_post_success_schema(self, async_client: AsyncClient):
        """Test that POST /api/v1/auth/login returns proper schema when credentials are valid."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Valid login request per OpenAPI schema
        login_data = {
            "email": "test@example.com",
            "password": "validpassword123"
        }

        response = await async_client.post("/api/v1/auth/login", json=login_data)

        # Contract validation - should return 200 with proper JSON structure
        assert response.status_code == 200

        json_data = response.json()

        # Validate response structure per OpenAPI schema
        required_fields = ["access_token", "token_type", "expires_in", "user"]
        for field in required_fields:
            assert field in json_data

        # Validate token fields
        assert isinstance(json_data["access_token"], str)
        assert json_data["token_type"] == "Bearer"
        assert isinstance(json_data["expires_in"], int)
        assert json_data["expires_in"] > 0

        # Validate user object structure
        user = json_data["user"]
        required_user_fields = ["id", "email", "name", "role", "organization_permissions", "created_at", "updated_at"]
        for field in required_user_fields:
            assert field in user

        # Validate user field types and formats
        assert uuid.UUID(user["id"])  # Should not raise ValueError
        assert isinstance(user["email"], str)
        assert isinstance(user["name"], str)
        assert len(user["name"]) <= 255

        # Validate email format
        assert "@" in user["email"]
        assert user["email"] == login_data["email"]

        # Validate role enum
        valid_roles = ["admin", "operator", "viewer"]
        assert user["role"] in valid_roles

        # Validate organization_permissions array
        assert isinstance(user["organization_permissions"], list)
        for org_id in user["organization_permissions"]:
            assert uuid.UUID(org_id)  # Each should be a valid UUID

        # Validate datetime format
        from datetime import datetime
        datetime.fromisoformat(user["created_at"].replace('Z', '+00:00'))
        datetime.fromisoformat(user["updated_at"].replace('Z', '+00:00'))

    @pytest.mark.asyncio
    async def test_auth_login_post_invalid_credentials(self, async_client: AsyncClient):
        """Test that POST /api/v1/auth/login returns 401 when credentials are invalid."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Invalid credentials
        login_data = {
            "email": "test@example.com",
            "password": "wrongpassword"
        }

        response = await async_client.post("/api/v1/auth/login", json=login_data)

        # Contract validation - should return 401 for invalid credentials
        assert response.status_code == 401

        json_data = response.json()

        # Validate error response (not specified in OpenAPI but expected)
        assert "error" in json_data or "detail" in json_data

    @pytest.mark.asyncio
    async def test_auth_login_post_missing_required_fields(self, async_client: AsyncClient):
        """Test that POST /api/v1/auth/login returns 422 when required fields are missing."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Missing email field
        response = await async_client.post("/api/v1/auth/login", json={"password": "validpassword123"})
        assert response.status_code == 422

        # Missing password field
        response = await async_client.post("/api/v1/auth/login", json={"email": "test@example.com"})
        assert response.status_code == 422

        # Missing both fields
        response = await async_client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

        # Empty request body
        response = await async_client.post("/api/v1/auth/login")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_auth_login_post_invalid_email_format(self, async_client: AsyncClient):
        """Test that POST /api/v1/auth/login returns 422 with invalid email format."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Invalid email format
        login_data = {
            "email": "not-an-email",
            "password": "validpassword123"
        }

        response = await async_client.post("/api/v1/auth/login", json=login_data)

        # Contract validation - should return 422 for invalid email format
        assert response.status_code == 422

        # Test with empty email
        login_data = {
            "email": "",
            "password": "validpassword123"
        }

        response = await async_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_auth_login_post_invalid_password_length(self, async_client: AsyncClient):
        """Test that POST /api/v1/auth/login returns 422 with password less than 8 characters."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Password too short (less than 8 characters per OpenAPI spec)
        login_data = {
            "email": "test@example.com",
            "password": "short"  # Only 5 characters
        }

        response = await async_client.post("/api/v1/auth/login", json=login_data)

        # Contract validation - should return 422 for password too short
        assert response.status_code == 422

        # Test with empty password
        login_data = {
            "email": "test@example.com",
            "password": ""
        }

        response = await async_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_auth_login_post_malformed_json(self, async_client: AsyncClient):
        """Test that POST /api/v1/auth/login returns 422 with malformed JSON."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Send malformed JSON
        response = await async_client.post(
            "/api/v1/auth/login",
            content='{"email": "test@example.com", "password":}',  # Malformed JSON
            headers={"content-type": "application/json"}
        )

        # Contract validation - should return 422 for malformed JSON
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_auth_login_post_wrong_content_type(self, async_client: AsyncClient):
        """Test that POST /api/v1/auth/login returns 422 with wrong content-type."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        # Send as form data instead of JSON
        response = await async_client.post(
            "/api/v1/auth/login",
            data={"email": "test@example.com", "password": "validpassword123"}
        )

        # Contract validation - should return 422 for wrong content-type
        assert response.status_code == 422

    def test_auth_login_post_content_type(self, client: TestClient):
        """Test that POST /api/v1/auth/login returns application/json content-type."""
        # This test should FAIL initially since the endpoint doesn't exist yet

        login_data = {
            "email": "test@example.com",
            "password": "validpassword123"
        }

        response = client.post("/api/v1/auth/login", json=login_data)

        # Content-type validation per OpenAPI spec
        assert response.headers.get("content-type") == "application/json"