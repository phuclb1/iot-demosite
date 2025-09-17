"""
Telemetry service for InfluxDB queries and data management.

Provides business logic layer for telemetry data operations including
current readings, historical queries, aggregations, and data processing.
"""

import logging
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from datetime import datetime, timedelta
from enum import Enum

from fastapi import HTTPException, Depends

from ..models.telemetry_reading import TelemetryReading, TelemetryField, AggregationInterval
from ..services.influxdb_service import get_influxdb_service, InfluxDBService
from ..services.postgresql_service import get_postgresql_service, PostgreSQLService


logger = logging.getLogger(__name__)


class TelemetryService:
    """Service class for telemetry data operations."""

    def __init__(self, influx_service: InfluxDBService, db_service: PostgreSQLService):
        """
        Initialize telemetry service.

        Args:
            influx_service: InfluxDB service for time-series data
            db_service: PostgreSQL service for metadata
        """
        self.influx_service = influx_service
        self.db_service = db_service

    async def get_current_telemetry(
        self,
        device_id: UUID,
        fields: Optional[List[TelemetryField]] = None
    ) -> Dict[str, Any]:
        """
        Get current (latest) telemetry readings for a device.

        Args:
            device_id: Device UUID
            fields: Optional list of specific fields to retrieve

        Returns:
            Dictionary with current telemetry values

        Raises:
            HTTPException: If device not found or query fails
        """
        try:
            # Verify device exists
            await self._verify_device_exists(device_id)

            # Get field names
            field_names = [field.value for field in fields] if fields else None

            # Query latest values
            latest_values = await self.influx_service.query_latest(
                measurement="telemetry_reading",
                device_id=str(device_id),
                fields=field_names,
                bucket="telemetry_raw"
            )

            if not latest_values:
                return {
                    'device_id': str(device_id),
                    'timestamp': None,
                    'readings': {}
                }

            # Format response
            readings = {}
            latest_timestamp = None

            for field_name, field_data in latest_values.items():
                readings[field_name] = {
                    'value': field_data['value'],
                    'unit': self._get_field_unit(field_name),
                    'timestamp': field_data['time']
                }

                # Track latest timestamp
                if latest_timestamp is None or field_data['time'] > latest_timestamp:
                    latest_timestamp = field_data['time']

            result = {
                'device_id': str(device_id),
                'timestamp': latest_timestamp,
                'readings': readings
            }

            logger.debug(f"Retrieved current telemetry for device {device_id}")
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get current telemetry for device {device_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve current telemetry"
            )

    async def get_historical_telemetry(
        self,
        device_id: UUID,
        start_time: datetime,
        end_time: datetime,
        fields: Optional[List[TelemetryField]] = None,
        interval: Optional[AggregationInterval] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get historical telemetry data for a device within time range.

        Args:
            device_id: Device UUID
            start_time: Query start time
            end_time: Query end time
            fields: Optional list of specific fields to retrieve
            interval: Optional aggregation interval
            limit: Optional limit on number of data points

        Returns:
            Dictionary with historical telemetry data

        Raises:
            HTTPException: If device not found or query fails
        """
        try:
            # Verify device exists
            await self._verify_device_exists(device_id)

            # Validate time range
            if start_time >= end_time:
                raise HTTPException(
                    status_code=400,
                    detail="Start time must be before end time"
                )

            # Get field names
            field_names = [field.value for field in fields] if fields else None

            # Convert interval to string
            interval_str = interval.value if interval else None

            # Query historical data
            historical_data = await self.influx_service.query_historical(
                measurement="telemetry_reading",
                device_id=str(device_id),
                start_time=start_time,
                end_time=end_time,
                fields=field_names,
                interval=interval_str,
                bucket="telemetry_raw"
            )

            # Apply limit if specified
            if limit and len(historical_data) > limit:
                # Take evenly distributed samples
                step = len(historical_data) // limit
                historical_data = historical_data[::max(1, step)][:limit]

            # Group data by timestamp
            grouped_data = {}
            for point in historical_data:
                timestamp = point.get('time', point.get('_time'))
                field_name = point.get('field', point.get('_field'))
                value = point.get('value', point.get('_value'))

                if timestamp not in grouped_data:
                    grouped_data[timestamp] = {}

                grouped_data[timestamp][field_name] = {
                    'value': value,
                    'unit': self._get_field_unit(field_name)
                }

            # Convert to list of time series data
            time_series = []
            for timestamp in sorted(grouped_data.keys()):
                time_series.append({
                    'timestamp': timestamp,
                    'readings': grouped_data[timestamp]
                })

            result = {
                'device_id': str(device_id),
                'start_time': start_time,
                'end_time': end_time,
                'interval': interval.value if interval else None,
                'data_points': len(time_series),
                'time_series': time_series
            }

            logger.debug(f"Retrieved {len(time_series)} historical points for device {device_id}")
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get historical telemetry for device {device_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve historical telemetry"
            )

    async def write_telemetry_reading(
        self,
        device_id: UUID,
        readings: Dict[str, float],
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Write telemetry reading to InfluxDB.

        Args:
            device_id: Device UUID
            readings: Dictionary of field name to value mappings
            timestamp: Optional timestamp (defaults to now)

        Returns:
            True if write was successful

        Raises:
            HTTPException: If device not found or write fails
        """
        try:
            # Verify device exists
            await self._verify_device_exists(device_id)

            # Validate readings
            validated_readings = {}
            for field_name, value in readings.items():
                if not isinstance(value, (int, float)):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid value for field '{field_name}': must be numeric"
                    )
                validated_readings[field_name] = float(value)

            # Write to InfluxDB
            await self.influx_service.write_point(
                measurement="telemetry_reading",
                tags={'device_id': str(device_id)},
                fields=validated_readings,
                timestamp=timestamp,
                bucket="telemetry_raw"
            )

            logger.debug(f"Wrote telemetry reading for device {device_id}")
            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to write telemetry reading for device {device_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to write telemetry reading"
            )

    async def write_telemetry_batch(
        self,
        readings: List[Dict[str, Any]]
    ) -> int:
        """
        Write multiple telemetry readings in batch.

        Args:
            readings: List of reading dictionaries with device_id, fields, timestamp

        Returns:
            Number of readings written

        Raises:
            HTTPException: If batch write fails
        """
        try:
            points = []

            for reading in readings:
                device_id = reading.get('device_id')
                fields = reading.get('fields', {})
                timestamp = reading.get('timestamp')

                if not device_id:
                    continue

                # Validate device exists (cache results to avoid repeated queries)
                await self._verify_device_exists(UUID(device_id))

                # Validate and convert fields
                validated_fields = {}
                for field_name, value in fields.items():
                    if isinstance(value, (int, float)):
                        validated_fields[field_name] = float(value)

                if validated_fields:
                    points.append({
                        'measurement': 'telemetry_reading',
                        'tags': {'device_id': str(device_id)},
                        'fields': validated_fields,
                        'timestamp': timestamp
                    })

            if points:
                await self.influx_service.write_points(points, bucket="telemetry_raw")

            logger.debug(f"Wrote {len(points)} telemetry readings in batch")
            return len(points)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to write telemetry batch: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to write telemetry batch"
            )

    async def get_aggregated_telemetry(
        self,
        device_id: UUID,
        field: TelemetryField,
        start_time: datetime,
        end_time: datetime,
        interval: AggregationInterval
    ) -> Dict[str, Any]:
        """
        Get aggregated telemetry data for a specific field.

        Args:
            device_id: Device UUID
            field: Telemetry field to aggregate
            start_time: Query start time
            end_time: Query end time
            interval: Aggregation interval

        Returns:
            Dictionary with aggregated data (min, max, mean, count)

        Raises:
            HTTPException: If device not found or query fails
        """
        try:
            # Verify device exists
            await self._verify_device_exists(device_id)

            # Build aggregation query
            query = f'''
                from(bucket: "telemetry_raw")
                    |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                    |> filter(fn: (r) => r._measurement == "telemetry_reading")
                    |> filter(fn: (r) => r.device_id == "{device_id}")
                    |> filter(fn: (r) => r._field == "{field.value}")
                    |> aggregateWindow(every: {interval.value}, fn: mean, createEmpty: false)
                    |> duplicate(column: "_value", as: "mean")
                    |> aggregateWindow(every: {interval.value}, fn: min, createEmpty: false)
                    |> duplicate(column: "_value", as: "min")
                    |> aggregateWindow(every: {interval.value}, fn: max, createEmpty: false)
                    |> duplicate(column: "_value", as: "max")
                    |> aggregateWindow(every: {interval.value}, fn: count, createEmpty: false)
                    |> duplicate(column: "_value", as: "count")
                    |> yield(name: "aggregated")
            '''

            results = await self.influx_service.query(query)

            # Process aggregated results
            aggregated_data = []
            for result in results:
                aggregated_data.append({
                    'timestamp': result.get('time', result.get('_time')),
                    'min': result.get('min'),
                    'max': result.get('max'),
                    'mean': result.get('mean'),
                    'count': result.get('count')
                })

            return {
                'device_id': str(device_id),
                'field': field.value,
                'unit': self._get_field_unit(field.value),
                'start_time': start_time,
                'end_time': end_time,
                'interval': interval.value,
                'data_points': len(aggregated_data),
                'aggregations': aggregated_data
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get aggregated telemetry for device {device_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to get aggregated telemetry"
            )

    async def get_device_telemetry_summary(
        self,
        device_id: UUID,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get telemetry summary for a device over specified hours.

        Args:
            device_id: Device UUID
            hours: Number of hours to look back

        Returns:
            Dictionary with telemetry summary statistics

        Raises:
            HTTPException: If device not found or query fails
        """
        try:
            # Verify device exists
            await self._verify_device_exists(device_id)

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)

            # Get summary statistics for all fields
            summary_query = f'''
                from(bucket: "telemetry_raw")
                    |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
                    |> filter(fn: (r) => r._measurement == "telemetry_reading")
                    |> filter(fn: (r) => r.device_id == "{device_id}")
                    |> group(columns: ["_field"])
                    |> aggregateWindow(every: inf, fn: mean, createEmpty: false)
                    |> duplicate(column: "_value", as: "mean")
                    |> min()
                    |> duplicate(column: "_value", as: "min")
                    |> max()
                    |> duplicate(column: "_value", as: "max")
                    |> count()
                    |> duplicate(column: "_value", as: "count")
                    |> yield(name: "summary")
            '''

            results = await self.influx_service.query(summary_query)

            # Process summary by field
            field_summaries = {}
            for result in results:
                field_name = result.get('field', result.get('_field'))
                if field_name not in field_summaries:
                    field_summaries[field_name] = {
                        'unit': self._get_field_unit(field_name)
                    }

                # Aggregate values
                if 'min' in result:
                    field_summaries[field_name]['min'] = result['min']
                elif 'max' in result:
                    field_summaries[field_name]['max'] = result['max']
                elif 'mean' in result:
                    field_summaries[field_name]['mean'] = result['mean']
                elif 'count' in result:
                    field_summaries[field_name]['count'] = result['count']

            return {
                'device_id': str(device_id),
                'summary_period_hours': hours,
                'start_time': start_time,
                'end_time': end_time,
                'field_summaries': field_summaries
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to get telemetry summary for device {device_id}: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to get telemetry summary"
            )

    async def _verify_device_exists(self, device_id: UUID) -> None:
        """
        Verify that a device exists in PostgreSQL.

        Args:
            device_id: Device UUID to verify

        Raises:
            HTTPException: If device doesn't exist
        """
        device_check_query = "SELECT id FROM devices WHERE id = $1"
        device_exists = await self.db_service.execute_query_one(device_check_query, device_id)
        if not device_exists:
            raise HTTPException(
                status_code=404,
                detail="Device not found"
            )

    def _get_field_unit(self, field_name: str) -> str:
        """
        Get the unit for a telemetry field.

        Args:
            field_name: Name of the telemetry field

        Returns:
            Unit string for the field
        """
        field_units = {
            'temperature': '°C',
            'vibration': 'mm/s',
            'power': 'W',
            'electricity': 'kWh'
        }
        return field_units.get(field_name, '')


async def get_telemetry_service(
    influx_service: InfluxDBService = Depends(get_influxdb_service),
    db_service: PostgreSQLService = Depends(get_postgresql_service)
) -> TelemetryService:
    """
    Dependency function to get telemetry service.

    Args:
        influx_service: InfluxDB service
        db_service: PostgreSQL database service

    Returns:
        Telemetry service instance
    """
    return TelemetryService(influx_service, db_service)