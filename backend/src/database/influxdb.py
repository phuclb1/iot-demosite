"""InfluxDB 3.0 connection and management for telemetry data."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from influxdb_client_3 import InfluxDBClient3, Point
except ImportError:
    # Fallback if influxdb3-python is not available
    class Point:
        pass
    class InfluxDBClient3:
        pass

from src.config import settings

logger = logging.getLogger(__name__)


class InfluxDBManager:
    """InfluxDB 3.0 connection manager for telemetry data."""

    def __init__(self):
        self._client: Optional[InfluxDBClient3] = None

    async def create_client(self) -> InfluxDBClient3:
        """Create and return an InfluxDB client."""
        if self._client is None:
            try:
                self._client = InfluxDBClient3(
                    host=settings.influxdb_url,
                    token=settings.influxdb_token,
                    org=settings.influxdb_org,
                    database=settings.influxdb_bucket,
                    timeout=30000,  # 30 seconds
                )
                logger.info(
                    f"InfluxDB client created: {settings.influxdb_url} -> {settings.influxdb_bucket}"
                )
            except Exception as e:
                logger.error(f"Failed to create InfluxDB client: {e}")
                raise
        return self._client

    async def close_client(self) -> None:
        """Close the InfluxDB client."""
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.warning(f"Error closing InfluxDB client: {e}")
            finally:
                self._client = None
                logger.info("InfluxDB client closed")

    @property
    def client(self) -> Optional[InfluxDBClient3]:
        """Get the InfluxDB client."""
        return self._client

    async def write_telemetry_data(
        self,
        device_id: str,
        organization: str,
        site: str,
        area: str,
        timestamp: datetime,
        vibration: float,
        temperature: float,
        power: float,
        electricity: float,
    ) -> None:
        """Write telemetry data to InfluxDB."""
        if not self._client:
            raise RuntimeError("InfluxDB client not initialized. Call create_client() first.")

        try:
            point = (
                Point("telemetry")
                .tag("device_id", device_id)
                .tag("organization", organization)
                .tag("site", site)
                .tag("area", area)
                .field("vibration", float(vibration))
                .field("temperature", float(temperature))
                .field("power", float(power))
                .field("electricity", float(electricity))
                .time(timestamp)
            )

            self._client.write(point)
            logger.debug(f"Telemetry data written for device {device_id}")

        except Exception as e:
            logger.error(f"Failed to write telemetry data for device {device_id}: {e}")
            raise

    async def write_telemetry_batch(self, telemetry_points: List[Dict[str, Any]]) -> None:
        """Write multiple telemetry data points in batch."""
        if not self._client:
            raise RuntimeError("InfluxDB client not initialized. Call create_client() first.")

        if not telemetry_points:
            logger.warning("No telemetry points to write")
            return

        try:
            points = []
            for data in telemetry_points:
                point = (
                    Point("telemetry")
                    .tag("device_id", data["device_id"])
                    .tag("organization", data["organization"])
                    .tag("site", data["site"])
                    .tag("area", data["area"])
                    .field("vibration", float(data["vibration"]))
                    .field("temperature", float(data["temperature"]))
                    .field("power", float(data["power"]))
                    .field("electricity", float(data["electricity"]))
                    .time(data["timestamp"])
                )
                points.append(point)

            self._client.write(points)
            logger.info(f"Batch write completed: {len(points)} telemetry points")

        except Exception as e:
            logger.error(f"Failed to write telemetry batch: {e}")
            raise

    async def query_current_telemetry(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Query the most recent telemetry data for a device."""
        if not self._client:
            raise RuntimeError("InfluxDB client not initialized. Call create_client() first.")

        try:
            query = f'''
            SELECT *
            FROM telemetry
            WHERE device_id = '{device_id}'
            ORDER BY time DESC
            LIMIT 1
            '''

            result = self._client.query(query)
            
            if result and len(result) > 0:
                record = result[0]
                return {
                    "device_id": record.get("device_id"),
                    "organization": record.get("organization"),
                    "site": record.get("site"),
                    "area": record.get("area"),
                    "timestamp": record.get("time"),
                    "vibration": record.get("vibration"),
                    "temperature": record.get("temperature"),
                    "power": record.get("power"),
                    "electricity": record.get("electricity"),
                }
            return None

        except Exception as e:
            logger.error(f"Failed to query current telemetry for device {device_id}: {e}")
            raise

    async def query_historical_telemetry(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Query historical telemetry data for a device within a time range."""
        if not self._client:
            raise RuntimeError("InfluxDB client not initialized. Call create_client() first.")

        try:
            query = f'''
            SELECT *
            FROM telemetry
            WHERE device_id = '{device_id}'
              AND time >= '{start_time.isoformat()}'
              AND time <= '{end_time.isoformat()}'
            ORDER BY time ASC
            LIMIT {limit}
            '''

            result = self._client.query(query)
            
            telemetry_data = []
            for record in result:
                telemetry_data.append({
                    "device_id": record.get("device_id"),
                    "organization": record.get("organization"),
                    "site": record.get("site"),
                    "area": record.get("area"),
                    "timestamp": record.get("time"),
                    "vibration": record.get("vibration"),
                    "temperature": record.get("temperature"),
                    "power": record.get("power"),
                    "electricity": record.get("electricity"),
                })

            logger.debug(f"Historical telemetry query returned {len(telemetry_data)} records")
            return telemetry_data

        except Exception as e:
            logger.error(f"Failed to query historical telemetry for device {device_id}: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if the InfluxDB connection is healthy."""
        try:
            if not self._client:
                return False
            
            # Simple query to check connectivity
            query = "SELECT * FROM telemetry LIMIT 1"
            self._client.query(query)
            return True
            
        except Exception as e:
            logger.error(f"InfluxDB health check failed: {e}")
            return False


# Global InfluxDB manager instance
influxdb_manager = InfluxDBManager()


async def init_influxdb() -> None:
    """Initialize InfluxDB client."""
    await influxdb_manager.create_client()


async def close_influxdb() -> None:
    """Close InfluxDB client."""
    await influxdb_manager.close_client()


def get_influxdb_client() -> InfluxDBClient3:
    """Get the InfluxDB client."""
    if not influxdb_manager.client:
        raise RuntimeError("InfluxDB client not initialized. Call init_influxdb() first.")
    return influxdb_manager.client