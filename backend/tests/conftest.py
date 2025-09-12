"""
Pytest configuration and shared fixtures for IoT Backend tests.
"""

import asyncio
import os
import pytest
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import the FastAPI app
from src.main import create_app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def app():
    """Create a FastAPI app for testing."""
    return create_app()


@pytest.fixture
def client(app) -> TestClient:
    """Create a test client for synchronous requests."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for async requests."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_postgres_service() -> MagicMock:
    """Mock PostgreSQL service."""
    return MagicMock()


@pytest.fixture
def mock_influxdb_service() -> AsyncMock:
    """Mock InfluxDB service."""
    return AsyncMock()


@pytest.fixture
def mock_mqtt_service() -> AsyncMock:
    """Mock MQTT service."""
    mock = AsyncMock()
    mock.connect = AsyncMock()
    mock.disconnect = AsyncMock()
    mock.subscribe = AsyncMock()
    mock.publish = AsyncMock()
    return mock


@pytest.fixture
def sample_telemetry_data() -> dict:
    """Sample telemetry data for testing."""
    return {
        "device_id": "device-001",
        "organization": "acme-corp",
        "site": "factory-01",
        "area": "production-floor",
        "timestamp": "2025-09-12T10:00:00Z",
        "vibration": 0.5,
        "temperature": 25.3,
        "power": 150.7,
        "electricity": 12.4
    }


@pytest.fixture
def sample_device_hierarchy() -> dict:
    """Sample device hierarchy for testing."""
    return {
        "organization": {
            "id": "org-001",
            "name": "ACME Corporation",
            "sites": [
                {
                    "id": "site-001",
                    "name": "Factory 01",
                    "areas": [
                        {
                            "id": "area-001",
                            "name": "Production Floor",
                            "devices": [
                                {
                                    "id": "device-001",
                                    "name": "Vibration Sensor 01",
                                    "type": "sensor",
                                    "status": "online"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }


# Test environment setup
@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ["TESTING"] = "1"
    os.environ["POSTGRES_DB"] = "iot_dashboard_test"
    os.environ["INFLUXDB_BUCKET"] = "telemetry_test"
    yield
    # Cleanup if needed