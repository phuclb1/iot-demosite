"""
InfluxDB connection and management service.

Provides connection management, query execution, and data writing utilities
for time-series telemetry data in the IoT dashboard.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
from influxdb_client.client.query_api import QueryApi
from influxdb_client.client.write_api import WriteApi
from influxdb_client.domain.write_precision import WritePrecision
from influxdb_client import Point
from fastapi import HTTPException


logger = logging.getLogger(__name__)


class InfluxDBService:
    """InfluxDB connection and data management service."""

    def __init__(
        self,
        url: str,
        token: str,
        org: str,
        bucket: str = "telemetry",
        timeout: int = 30000
    ):
        """
        Initialize InfluxDB service.

        Args:
            url: InfluxDB server URL
            token: Authentication token
            org: Organization name
            bucket: Default bucket name
            timeout: Request timeout in milliseconds
        """
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.timeout = timeout
        self._client: Optional[InfluxDBClient] = None
        self._write_api: Optional[WriteApi] = None
        self._query_api: Optional[QueryApi] = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize InfluxDB client and APIs."""
        async with self._lock:
            if self._client is None:
                try:
                    self._client = InfluxDBClient(
                        url=self.url,
                        token=self.token,
                        org=self.org,
                        timeout=self.timeout
                    )

                    # Initialize APIs
                    self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
                    self._query_api = self._client.query_api()

                    logger.info(f"InfluxDB client initialized: {self.url}")

                    # Test connection
                    await self.health_check()

                except Exception as e:
                    logger.error(f"Failed to initialize InfluxDB client: {e}")
                    raise

    async def close(self) -> None:
        """Close InfluxDB client and APIs."""
        async with self._lock:
            if self._write_api:
                self._write_api.close()
                self._write_api = None

            if self._client:
                self._client.close()
                self._client = None

            logger.info("InfluxDB client closed")

    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._client is not None

    def _ensure_initialized(self) -> None:
        """Ensure service is initialized."""
        if not self.is_initialized:
            raise HTTPException(
                status_code=500,
                detail="InfluxDB service not initialized"
            )

    async def write_point(
        self,
        measurement: str,
        tags: Dict[str, str],
        fields: Dict[str, Any],
        timestamp: Optional[datetime] = None,
        bucket: Optional[str] = None
    ) -> None:
        """
        Write single data point to InfluxDB.

        Args:
            measurement: Measurement name
            tags: Tag dictionary
            fields: Field dictionary
            timestamp: Optional timestamp (defaults to now)
            bucket: Optional bucket (defaults to service bucket)

        Raises:
            HTTPException: If write operation fails
        """
        self._ensure_initialized()

        try:
            point = Point(measurement)

            # Add tags
            for tag_key, tag_value in tags.items():
                point.tag(tag_key, tag_value)

            # Add fields
            for field_key, field_value in fields.items():
                point.field(field_key, field_value)

            # Set timestamp
            if timestamp:
                point.time(timestamp, WritePrecision.NS)

            # Write point
            self._write_api.write(
                bucket=bucket or self.bucket,
                org=self.org,
                record=point
            )

        except Exception as e:
            logger.error(f"Failed to write point to InfluxDB: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to write data: {str(e)}"
            )

    async def write_points(
        self,
        points: List[Dict[str, Any]],
        bucket: Optional[str] = None
    ) -> None:
        """
        Write multiple data points to InfluxDB.

        Args:
            points: List of point dictionaries with measurement, tags, fields, timestamp
            bucket: Optional bucket (defaults to service bucket)

        Raises:
            HTTPException: If write operation fails
        """
        self._ensure_initialized()

        try:
            influx_points = []

            for point_data in points:
                point = Point(point_data['measurement'])

                # Add tags
                if 'tags' in point_data:
                    for tag_key, tag_value in point_data['tags'].items():
                        point.tag(tag_key, tag_value)

                # Add fields
                if 'fields' in point_data:
                    for field_key, field_value in point_data['fields'].items():
                        point.field(field_key, field_value)

                # Set timestamp
                if 'timestamp' in point_data and point_data['timestamp']:
                    point.time(point_data['timestamp'], WritePrecision.NS)

                influx_points.append(point)

            # Write points
            self._write_api.write(
                bucket=bucket or self.bucket,
                org=self.org,
                record=influx_points
            )

        except Exception as e:
            logger.error(f"Failed to write points to InfluxDB: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to write data: {str(e)}"
            )

    async def query(
        self,
        query: str,
        bucket: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute Flux query and return results.

        Args:
            query: Flux query string
            bucket: Optional bucket (defaults to service bucket)
            params: Optional query parameters

        Returns:
            List of query result records

        Raises:
            HTTPException: If query execution fails
        """
        self._ensure_initialized()

        try:
            # Replace bucket placeholder if needed
            if "{bucket}" in query:
                query = query.replace("{bucket}", f'"{bucket or self.bucket}"')

            # Execute query
            tables = self._query_api.query(query, org=self.org, params=params)

            # Convert results to list of dictionaries
            results = []
            for table in tables:
                for record in table.records:
                    result = {
                        'time': record.get_time(),
                        'measurement': record.get_measurement(),
                        'field': record.get_field(),
                        'value': record.get_value()
                    }

                    # Add tags
                    if record.values:
                        for key, value in record.values.items():
                            if key.startswith('_') or key in ['result', 'table']:
                                continue
                            result[key] = value

                    results.append(result)

            return results

        except Exception as e:
            logger.error(f"InfluxDB query failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Query execution failed: {str(e)}"
            )

    async def query_latest(
        self,
        measurement: str,
        device_id: str,
        fields: Optional[List[str]] = None,
        bucket: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query latest values for a device.

        Args:
            measurement: Measurement name
            device_id: Device identifier
            fields: Optional list of fields to retrieve
            bucket: Optional bucket (defaults to service bucket)

        Returns:
            Dictionary with latest field values

        Raises:
            HTTPException: If query execution fails
        """
        field_filter = ""
        if fields:
            field_list = '", "'.join(fields)
            field_filter = f'|> filter(fn: (r) => contains(value: r._field, set: ["{field_list}"]))'

        query = f'''
            from(bucket: {bucket or self.bucket})
                |> range(start: -1h)
                |> filter(fn: (r) => r._measurement == "{measurement}")
                |> filter(fn: (r) => r.device_id == "{device_id}")
                {field_filter}
                |> last()
                |> yield(name: "latest")
        '''

        results = await self.query(query, bucket)

        # Group results by field
        latest_values = {}
        for result in results:
            field_name = result.get('field', result.get('_field'))
            if field_name:
                latest_values[field_name] = {
                    'value': result.get('value', result.get('_value')),
                    'time': result.get('time', result.get('_time'))
                }

        return latest_values

    async def query_historical(
        self,
        measurement: str,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
        fields: Optional[List[str]] = None,
        interval: Optional[str] = None,
        bucket: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query historical data for a device within time range.

        Args:
            measurement: Measurement name
            device_id: Device identifier
            start_time: Query start time
            end_time: Query end time
            fields: Optional list of fields to retrieve
            interval: Optional aggregation interval (e.g., "1m", "5m", "1h")
            bucket: Optional bucket (defaults to service bucket)

        Returns:
            List of historical data points

        Raises:
            HTTPException: If query execution fails
        """
        field_filter = ""
        if fields:
            field_list = '", "'.join(fields)
            field_filter = f'|> filter(fn: (r) => contains(value: r._field, set: ["{field_list}"]))'

        aggregation = ""
        if interval:
            aggregation = f'|> aggregateWindow(every: {interval}, fn: mean, createEmpty: false)'

        query = f'''
            from(bucket: {bucket or self.bucket})
                |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                |> filter(fn: (r) => r._measurement == "{measurement}")
                |> filter(fn: (r) => r.device_id == "{device_id}")
                {field_filter}
                {aggregation}
                |> sort(columns: ["_time"])
                |> yield(name: "historical")
        '''

        return await self.query(query, bucket)

    async def query_device_status(
        self,
        device_id: str,
        start_time: Optional[datetime] = None,
        bucket: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Query device status information.

        Args:
            device_id: Device identifier
            start_time: Optional start time (defaults to last 24 hours)
            bucket: Optional bucket (defaults to device_status bucket)

        Returns:
            Device status information

        Raises:
            HTTPException: If query execution fails
        """
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(hours=24)

        status_bucket = bucket or "device_status"

        query = f'''
            from(bucket: "{status_bucket}")
                |> range(start: {start_time.isoformat()})
                |> filter(fn: (r) => r._measurement == "device_status_snapshot")
                |> filter(fn: (r) => r.device_id == "{device_id}")
                |> last()
                |> yield(name: "status")
        '''

        results = await self.query(query, status_bucket)

        if not results:
            return {'status': 'unknown', 'last_seen': None}

        latest = results[0]
        return {
            'status': latest.get('value', latest.get('_value')),
            'last_seen': latest.get('time', latest.get('_time')),
            'device_id': device_id
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform InfluxDB health check.

        Returns:
            Health check status and metrics

        Raises:
            HTTPException: If health check fails
        """
        try:
            start_time = asyncio.get_event_loop().time()

            # Check InfluxDB health
            health = self._client.health()

            response_time = asyncio.get_event_loop().time() - start_time

            if health.status == "pass":
                return {
                    'status': 'healthy',
                    'message': health.message,
                    'response_time_ms': round(response_time * 1000, 2),
                    'timestamp': asyncio.get_event_loop().time()
                }
            else:
                logger.error(f"InfluxDB health check failed: {health.message}")
                raise HTTPException(
                    status_code=500,
                    detail=f"InfluxDB unhealthy: {health.message}"
                )

        except Exception as e:
            logger.error(f"InfluxDB health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': asyncio.get_event_loop().time()
            }

    async def list_buckets(self) -> List[Dict[str, Any]]:
        """
        List available buckets.

        Returns:
            List of bucket information

        Raises:
            HTTPException: If operation fails
        """
        self._ensure_initialized()

        try:
            buckets_api = self._client.buckets_api()
            buckets = buckets_api.find_buckets()

            return [
                {
                    'id': bucket.id,
                    'name': bucket.name,
                    'description': bucket.description,
                    'retention_rules': bucket.retention_rules
                }
                for bucket in buckets.buckets
            ]

        except Exception as e:
            logger.error(f"Failed to list buckets: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to list buckets: {str(e)}"
            )


# Global service instance
influxdb_service: Optional[InfluxDBService] = None


async def get_influxdb_service() -> InfluxDBService:
    """
    Dependency function to get InfluxDB service instance.

    Returns:
        InfluxDB service instance

    Raises:
        HTTPException: If service not initialized
    """
    global influxdb_service

    if influxdb_service is None:
        raise HTTPException(
            status_code=500,
            detail="InfluxDB service not initialized"
        )

    return influxdb_service


async def initialize_influxdb_service(
    url: str,
    token: str,
    org: str,
    bucket: str = "telemetry",
    **kwargs
) -> InfluxDBService:
    """
    Initialize global InfluxDB service instance.

    Args:
        url: InfluxDB server URL
        token: Authentication token
        org: Organization name
        bucket: Default bucket name
        **kwargs: Additional configuration

    Returns:
        Initialized InfluxDB service
    """
    global influxdb_service

    influxdb_service = InfluxDBService(url, token, org, bucket, **kwargs)
    await influxdb_service.initialize()

    return influxdb_service


async def close_influxdb_service() -> None:
    """Close global InfluxDB service instance."""
    global influxdb_service

    if influxdb_service:
        await influxdb_service.close()
        influxdb_service = None