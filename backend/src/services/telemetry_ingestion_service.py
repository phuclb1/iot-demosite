"""
Telemetry ingestion service for MQTT to InfluxDB data pipeline.

Handles real-time ingestion of telemetry data from MQTT brokers into InfluxDB,
with buffering, batch processing, and error recovery capabilities.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import json
import time

import asyncio_mqtt as aiomqtt
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import ASYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError

from .mqtt_message_parser import mqtt_parser, ValidationResult, MessageType

# Setup logging
logger = logging.getLogger(__name__)


@dataclass
class IngestionConfig:
    """Configuration for telemetry ingestion service."""
    # MQTT Configuration
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    mqtt_topics: List[str] = field(default_factory=lambda: ["iot/+/+/+/+/telemetry"])
    mqtt_qos: int = 1
    mqtt_client_id: str = "telemetry_ingestion"

    # InfluxDB Configuration
    influxdb_url: str = "http://localhost:8086"
    influxdb_token: str = ""
    influxdb_org: str = "iot-org"
    influxdb_bucket: str = "telemetry"

    # Ingestion Configuration
    batch_size: int = 100
    batch_timeout_seconds: float = 5.0
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    buffer_size: int = 10000
    health_check_interval: int = 30

    # Processing Configuration
    enable_validation: bool = True
    enable_deduplication: bool = True
    deduplication_window_minutes: int = 5


@dataclass
class IngestionMetrics:
    """Metrics for telemetry ingestion service."""
    total_messages_received: int = 0
    valid_messages: int = 0
    invalid_messages: int = 0
    duplicate_messages: int = 0
    influxdb_writes: int = 0
    influxdb_write_errors: int = 0
    last_message_time: Optional[datetime] = None
    service_start_time: datetime = field(default_factory=datetime.utcnow)
    last_health_check: Optional[datetime] = None

    def get_processing_rate(self) -> float:
        """Calculate messages per second processing rate."""
        if not self.last_message_time:
            return 0.0

        duration = (datetime.utcnow() - self.service_start_time).total_seconds()
        return self.total_messages_received / duration if duration > 0 else 0.0

    def get_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_messages_received == 0:
            return 100.0
        return (self.valid_messages / self.total_messages_received) * 100


class TelemetryBuffer:
    """Buffer for batching telemetry data before writing to InfluxDB."""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.buffer: List[Dict[str, Any]] = []
        self.lock = asyncio.Lock()

    async def add(self, telemetry_data: Dict[str, Any]) -> bool:
        """Add telemetry data to buffer."""
        async with self.lock:
            if len(self.buffer) >= self.max_size:
                logger.warning("Buffer full, dropping oldest data")
                self.buffer.pop(0)

            self.buffer.append(telemetry_data)
            return True

    async def get_batch(self, batch_size: int) -> List[Dict[str, Any]]:
        """Get a batch of telemetry data."""
        async with self.lock:
            batch = self.buffer[:batch_size]
            self.buffer = self.buffer[batch_size:]
            return batch

    async def size(self) -> int:
        """Get current buffer size."""
        async with self.lock:
            return len(self.buffer)

    async def clear(self):
        """Clear all buffered data."""
        async with self.lock:
            self.buffer.clear()


class DeduplicationCache:
    """Cache for detecting duplicate messages."""

    def __init__(self, window_minutes: int = 5):
        self.window_minutes = window_minutes
        self.cache: Dict[str, datetime] = {}
        self.lock = asyncio.Lock()

    async def is_duplicate(self, device_id: str, timestamp: datetime, sequence_number: Optional[int] = None) -> bool:
        """Check if message is a duplicate."""
        async with self.lock:
            # Create unique key
            key = f"{device_id}:{timestamp.isoformat()}"
            if sequence_number is not None:
                key += f":{sequence_number}"

            # Check if already seen
            if key in self.cache:
                return True

            # Add to cache
            self.cache[key] = datetime.utcnow()

            # Clean old entries
            await self._cleanup_old_entries()
            return False

    async def _cleanup_old_entries(self):
        """Remove old entries from cache."""
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.window_minutes)
        keys_to_remove = [
            key for key, timestamp in self.cache.items()
            if timestamp < cutoff_time
        ]
        for key in keys_to_remove:
            del self.cache[key]


class TelemetryIngestionService:
    """Main telemetry ingestion service."""

    def __init__(self, config: IngestionConfig):
        self.config = config
        self.metrics = IngestionMetrics()
        self.buffer = TelemetryBuffer(config.buffer_size)
        self.deduplication_cache = DeduplicationCache(config.deduplication_window_minutes)

        # Service state
        self.running = False
        self.mqtt_client: Optional[aiomqtt.Client] = None
        self.influxdb_client: Optional[InfluxDBClient] = None
        self.write_api = None

        # Tasks
        self.background_tasks: List[asyncio.Task] = []

    async def start(self):
        """Start the ingestion service."""
        if self.running:
            logger.warning("Service already running")
            return

        logger.info("Starting telemetry ingestion service")

        try:
            # Initialize clients
            await self._initialize_clients()

            # Start background tasks
            self.running = True
            self._start_background_tasks()

            # Start MQTT message processing
            await self._start_mqtt_processing()

        except Exception as e:
            logger.error(f"Failed to start ingestion service: {e}")
            await self.stop()
            raise

    async def stop(self):
        """Stop the ingestion service."""
        logger.info("Stopping telemetry ingestion service")

        self.running = False

        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)

        # Close clients
        if self.mqtt_client:
            await self.mqtt_client.disconnect()

        if self.influxdb_client:
            self.influxdb_client.close()

        logger.info("Ingestion service stopped")

    async def _initialize_clients(self):
        """Initialize MQTT and InfluxDB clients."""
        # Initialize InfluxDB client
        self.influxdb_client = InfluxDBClient(
            url=self.config.influxdb_url,
            token=self.config.influxdb_token,
            org=self.config.influxdb_org
        )

        # Test InfluxDB connection
        try:
            health = self.influxdb_client.health()
            if health.status != "pass":
                raise Exception(f"InfluxDB health check failed: {health.message}")
            logger.info("InfluxDB connection established")
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            raise

        # Initialize write API
        self.write_api = self.influxdb_client.write_api(write_options=ASYNCHRONOUS)

        # Initialize MQTT client
        self.mqtt_client = aiomqtt.Client(
            hostname=self.config.mqtt_host,
            port=self.config.mqtt_port,
            username=self.config.mqtt_username,
            password=self.config.mqtt_password,
            identifier=self.config.mqtt_client_id
        )

    def _start_background_tasks(self):
        """Start background processing tasks."""
        # Batch processing task
        self.background_tasks.append(
            asyncio.create_task(self._batch_processor())
        )

        # Health check task
        self.background_tasks.append(
            asyncio.create_task(self._health_checker())
        )

        # Metrics logger task
        self.background_tasks.append(
            asyncio.create_task(self._metrics_logger())
        )

    async def _start_mqtt_processing(self):
        """Start processing MQTT messages."""
        try:
            async with self.mqtt_client:
                # Subscribe to topics
                for topic in self.config.mqtt_topics:
                    await self.mqtt_client.subscribe(topic, qos=self.config.mqtt_qos)
                    logger.info(f"Subscribed to MQTT topic: {topic}")

                # Process messages
                async for message in self.mqtt_client.messages:
                    if not self.running:
                        break

                    await self._process_mqtt_message(message)

        except Exception as e:
            logger.error(f"MQTT processing error: {e}")
            if self.running:
                # Attempt reconnection
                await asyncio.sleep(self.config.retry_delay_seconds)
                if self.running:
                    await self._start_mqtt_processing()

    async def _process_mqtt_message(self, message):
        """Process individual MQTT message."""
        try:
            self.metrics.total_messages_received += 1
            self.metrics.last_message_time = datetime.utcnow()

            # Parse and validate message
            if self.config.enable_validation:
                validation_result = mqtt_parser.validate_message(
                    message.topic.value, message.payload
                )

                if not validation_result.is_valid:
                    self.metrics.invalid_messages += 1
                    logger.warning(f"Invalid message from {message.topic}: {validation_result.errors}")
                    return

                self.metrics.valid_messages += 1

                # Extract telemetry data
                telemetry_data = mqtt_parser.extract_telemetry_data(validation_result)
                if not telemetry_data:
                    # Non-telemetry message (status, heartbeat, etc.)
                    await self._handle_non_telemetry_message(validation_result)
                    return

            else:
                # Skip validation, parse directly
                try:
                    payload_data = mqtt_parser.parse_payload(message.payload)
                    topic_info = mqtt_parser.parse_topic(message.topic.value)

                    # Basic telemetry data structure
                    telemetry_data = {
                        'measurement': 'device_telemetry',
                        'tags': {
                            'device_id': topic_info['device_id'],
                            'organization': topic_info['organization_slug'],
                            'site': topic_info['site_slug'],
                            'area': topic_info['area_slug']
                        },
                        'timestamp': datetime.utcnow(),
                        'fields': payload_data
                    }
                except Exception as e:
                    self.metrics.invalid_messages += 1
                    logger.warning(f"Failed to parse message: {e}")
                    return

            # Check for duplicates
            if self.config.enable_deduplication:
                device_id = telemetry_data['tags']['device_id']
                timestamp = telemetry_data['timestamp']
                sequence_number = telemetry_data['fields'].get('sequence_number')

                if await self.deduplication_cache.is_duplicate(device_id, timestamp, sequence_number):
                    self.metrics.duplicate_messages += 1
                    logger.debug(f"Duplicate message detected from {device_id}")
                    return

            # Add to buffer
            await self.buffer.add(telemetry_data)

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    async def _handle_non_telemetry_message(self, validation_result: ValidationResult):
        """Handle non-telemetry messages (status, alerts, etc.)."""
        message_data = validation_result.parsed_data['message']
        message_type = message_data['message_type']

        if message_type == MessageType.STATUS:
            # Update device status in separate measurement
            await self._write_device_status(validation_result)
        elif message_type == MessageType.ALERT:
            # Write alert to alerts measurement
            await self._write_device_alert(validation_result)
        # Add more handlers as needed

    async def _write_device_status(self, validation_result: ValidationResult):
        """Write device status to InfluxDB."""
        try:
            message_data = validation_result.parsed_data['message']
            topic_info = validation_result.parsed_data['topic_info']

            status_data = {
                'measurement': 'device_status',
                'tags': {
                    'device_id': message_data['device_id'],
                    'organization': topic_info['organization_slug'],
                    'site': topic_info['site_slug'],
                    'area': topic_info['area_slug']
                },
                'timestamp': message_data['timestamp'],
                'fields': {
                    'status': message_data['status'],
                    'battery_level': message_data.get('battery_level'),
                    'signal_strength': message_data.get('signal_strength'),
                    'firmware_version': message_data.get('firmware_version'),
                    'uptime_seconds': message_data.get('uptime_seconds')
                }
            }

            # Remove None values
            status_data['fields'] = {k: v for k, v in status_data['fields'].items() if v is not None}

            await self.buffer.add(status_data)

        except Exception as e:
            logger.error(f"Failed to write device status: {e}")

    async def _write_device_alert(self, validation_result: ValidationResult):
        """Write device alert to InfluxDB."""
        try:
            message_data = validation_result.parsed_data['message']
            topic_info = validation_result.parsed_data['topic_info']

            alert_data = {
                'measurement': 'device_alerts',
                'tags': {
                    'device_id': message_data['device_id'],
                    'organization': topic_info['organization_slug'],
                    'site': topic_info['site_slug'],
                    'area': topic_info['area_slug'],
                    'alert_type': message_data['alert_type'],
                    'severity': message_data['severity']
                },
                'timestamp': message_data['timestamp'],
                'fields': {
                    'description': message_data['description'],
                    'alert_code': message_data.get('alert_code'),
                    'acknowledgment_required': message_data['acknowledgment_required']
                }
            }

            # Remove None values
            alert_data['fields'] = {k: v for k, v in alert_data['fields'].items() if v is not None}

            await self.buffer.add(alert_data)

        except Exception as e:
            logger.error(f"Failed to write device alert: {e}")

    async def _batch_processor(self):
        """Background task to process batches of telemetry data."""
        while self.running:
            try:
                buffer_size = await self.buffer.size()

                if buffer_size == 0:
                    await asyncio.sleep(0.1)
                    continue

                # Determine batch size
                batch_size = min(self.config.batch_size, buffer_size)

                # Get batch
                batch = await self.buffer.get_batch(batch_size)

                if batch:
                    await self._write_batch_to_influxdb(batch)

                # Wait for next batch
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"Batch processor error: {e}")
                await asyncio.sleep(1.0)

    async def _write_batch_to_influxdb(self, batch: List[Dict[str, Any]]):
        """Write batch of telemetry data to InfluxDB."""
        try:
            # Convert to InfluxDB points
            points = []
            for data in batch:
                point = Point(data['measurement'])

                # Add tags
                for tag_key, tag_value in data['tags'].items():
                    point = point.tag(tag_key, tag_value)

                # Add fields
                for field_key, field_value in data['fields'].items():
                    if field_value is not None:
                        point = point.field(field_key, field_value)

                # Set timestamp
                point = point.time(data['timestamp'])
                points.append(point)

            # Write to InfluxDB
            await self._write_points_with_retry(points)

            self.metrics.influxdb_writes += len(points)
            logger.debug(f"Successfully wrote {len(points)} points to InfluxDB")

        except Exception as e:
            self.metrics.influxdb_write_errors += 1
            logger.error(f"Failed to write batch to InfluxDB: {e}")

            # Re-add failed data to buffer for retry
            for data in batch:
                await self.buffer.add(data)

    async def _write_points_with_retry(self, points: List[Point]):
        """Write points to InfluxDB with retry logic."""
        for attempt in range(self.config.max_retries):
            try:
                # Use synchronous write for better error handling
                self.influxdb_client.write_api().write(
                    bucket=self.config.influxdb_bucket,
                    record=points
                )
                return  # Success

            except InfluxDBError as e:
                logger.warning(f"InfluxDB write attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds * (attempt + 1))
                else:
                    raise

    async def _health_checker(self):
        """Background task for health monitoring."""
        while self.running:
            try:
                # Check InfluxDB health
                if self.influxdb_client:
                    health = self.influxdb_client.health()
                    if health.status != "pass":
                        logger.warning(f"InfluxDB health check failed: {health.message}")

                self.metrics.last_health_check = datetime.utcnow()

                await asyncio.sleep(self.config.health_check_interval)

            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(self.config.health_check_interval)

    async def _metrics_logger(self):
        """Background task to log metrics periodically."""
        while self.running:
            try:
                logger.info(
                    f"Ingestion metrics - "
                    f"Total: {self.metrics.total_messages_received}, "
                    f"Valid: {self.metrics.valid_messages}, "
                    f"Invalid: {self.metrics.invalid_messages}, "
                    f"Rate: {self.metrics.get_processing_rate():.2f} msg/s, "
                    f"Success: {self.metrics.get_success_rate():.1f}%, "
                    f"Buffer: {await self.buffer.size()}"
                )

                await asyncio.sleep(60)  # Log every minute

            except Exception as e:
                logger.error(f"Metrics logger error: {e}")
                await asyncio.sleep(60)

    async def get_metrics(self) -> Dict[str, Any]:
        """Get current service metrics."""
        buffer_size = await self.buffer.size()

        return {
            'total_messages_received': self.metrics.total_messages_received,
            'valid_messages': self.metrics.valid_messages,
            'invalid_messages': self.metrics.invalid_messages,
            'duplicate_messages': self.metrics.duplicate_messages,
            'influxdb_writes': self.metrics.influxdb_writes,
            'influxdb_write_errors': self.metrics.influxdb_write_errors,
            'processing_rate_per_second': self.metrics.get_processing_rate(),
            'success_rate_percentage': self.metrics.get_success_rate(),
            'buffer_size': buffer_size,
            'service_uptime_seconds': (datetime.utcnow() - self.metrics.service_start_time).total_seconds(),
            'last_message_time': self.metrics.last_message_time.isoformat() if self.metrics.last_message_time else None,
            'last_health_check': self.metrics.last_health_check.isoformat() if self.metrics.last_health_check else None,
            'is_running': self.running
        }


# Global service instance
_ingestion_service: Optional[TelemetryIngestionService] = None


async def start_ingestion_service(config: IngestionConfig) -> TelemetryIngestionService:
    """Start the global telemetry ingestion service."""
    global _ingestion_service

    if _ingestion_service and _ingestion_service.running:
        logger.warning("Ingestion service already running")
        return _ingestion_service

    _ingestion_service = TelemetryIngestionService(config)
    await _ingestion_service.start()
    return _ingestion_service


async def stop_ingestion_service():
    """Stop the global telemetry ingestion service."""
    global _ingestion_service

    if _ingestion_service:
        await _ingestion_service.stop()
        _ingestion_service = None


def get_ingestion_service() -> Optional[TelemetryIngestionService]:
    """Get the current ingestion service instance."""
    return _ingestion_service