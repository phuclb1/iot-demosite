"""
MQTT client service for IoT device communication.

Provides MQTT client management, message handling, and telemetry data ingestion
from IoT devices with automatic reconnection and error handling.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Callable, List
from uuid import UUID
from datetime import datetime

import asyncio_mqtt
from asyncio_mqtt import Client, MqttError
from fastapi import HTTPException, Depends

from ..services.telemetry_service import get_telemetry_service, TelemetryService
from ..services.device_service import get_device_service, DeviceService
from ..models.device import DeviceStatus


logger = logging.getLogger(__name__)


class MQTTService:
    """MQTT client service for IoT device communication."""

    def __init__(
        self,
        broker_host: str,
        broker_port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        telemetry_service: Optional[TelemetryService] = None,
        device_service: Optional[DeviceService] = None
    ):
        """
        Initialize MQTT service.

        Args:
            broker_host: MQTT broker hostname
            broker_port: MQTT broker port
            username: Optional MQTT username
            password: Optional MQTT password
            telemetry_service: Telemetry service for data processing
            device_service: Device service for status updates
        """
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        self.telemetry_service = telemetry_service
        self.device_service = device_service

        self._client: Optional[Client] = None
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._message_handlers: Dict[str, Callable] = {}
        self._reconnect_interval = 5.0
        self._max_reconnect_attempts = 10
        self._reconnect_attempts = 0

        # Default topic patterns
        self.telemetry_topic = "telemetry/+/data"
        self.status_topic = "telemetry/+/status"
        self.heartbeat_topic = "telemetry/+/heartbeat"

        # Setup default message handlers
        self._setup_default_handlers()

    def _setup_default_handlers(self):
        """Setup default MQTT message handlers."""
        self._message_handlers = {
            "telemetry/*/data": self._handle_telemetry_data,
            "telemetry/*/status": self._handle_device_status,
            "telemetry/*/heartbeat": self._handle_device_heartbeat,
        }

    async def initialize(self) -> None:
        """Initialize MQTT client and start connection."""
        try:
            await self._connect()
            await self._subscribe_to_topics()
            self._running = True

            # Start message processing task
            task = asyncio.create_task(self._message_loop())
            self._tasks.append(task)

            logger.info(f"MQTT service initialized and connected to {self.broker_host}:{self.broker_port}")

        except Exception as e:
            logger.error(f"Failed to initialize MQTT service: {e}")
            raise

    async def close(self) -> None:
        """Close MQTT client and cleanup tasks."""
        self._running = False

        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        # Disconnect client
        if self._client:
            await self._client.disconnect()
            self._client = None

        logger.info("MQTT service closed")

    async def _connect(self) -> None:
        """Connect to MQTT broker with authentication."""
        try:
            self._client = Client(
                hostname=self.broker_host,
                port=self.broker_port,
                username=self.username,
                password=self.password,
                client_id="iot_telemetry_dashboard",
                keepalive=60,
                will=asyncio_mqtt.Will(
                    topic="system/dashboard/status",
                    payload="offline",
                    qos=1,
                    retain=True
                )
            )

            await self._client.connect()
            self._reconnect_attempts = 0

            # Publish online status
            await self._client.publish(
                "system/dashboard/status",
                payload="online",
                qos=1,
                retain=True
            )

            logger.info("Connected to MQTT broker")

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise

    async def _subscribe_to_topics(self) -> None:
        """Subscribe to MQTT topics for telemetry data."""
        try:
            topics = [
                self.telemetry_topic,
                self.status_topic,
                self.heartbeat_topic
            ]

            for topic in topics:
                await self._client.subscribe(topic, qos=1)
                logger.debug(f"Subscribed to MQTT topic: {topic}")

        except Exception as e:
            logger.error(f"Failed to subscribe to MQTT topics: {e}")
            raise

    async def _message_loop(self) -> None:
        """Main message processing loop with reconnection handling."""
        while self._running:
            try:
                if not self._client:
                    await self._connect()
                    await self._subscribe_to_topics()

                async with self._client.messages() as messages:
                    async for message in messages:
                        try:
                            await self._process_message(message)
                        except Exception as e:
                            logger.error(f"Error processing MQTT message: {e}")

            except MqttError as e:
                logger.error(f"MQTT connection error: {e}")
                await self._handle_reconnection()

            except Exception as e:
                logger.error(f"Unexpected error in MQTT message loop: {e}")
                await asyncio.sleep(1)

    async def _handle_reconnection(self) -> None:
        """Handle MQTT reconnection with exponential backoff."""
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error("Maximum reconnection attempts reached, stopping MQTT service")
            self._running = False
            return

        self._reconnect_attempts += 1
        wait_time = min(self._reconnect_interval * (2 ** self._reconnect_attempts), 60)

        logger.warning(f"MQTT reconnection attempt {self._reconnect_attempts} in {wait_time}s")
        await asyncio.sleep(wait_time)

        try:
            if self._client:
                await self._client.disconnect()
            self._client = None
        except:
            pass

    async def _process_message(self, message) -> None:
        """Process incoming MQTT message."""
        try:
            topic = message.topic.value
            payload = message.payload.decode('utf-8')

            logger.debug(f"Received MQTT message on topic {topic}: {payload}")

            # Find matching handler
            handler = self._find_handler(topic)
            if handler:
                await handler(topic, payload)
            else:
                logger.warning(f"No handler found for MQTT topic: {topic}")

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _find_handler(self, topic: str) -> Optional[Callable]:
        """Find message handler for given topic."""
        for pattern, handler in self._message_handlers.items():
            if self._topic_matches(topic, pattern):
                return handler
        return None

    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern with wildcards."""
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')

        if len(topic_parts) != len(pattern_parts):
            return False

        for topic_part, pattern_part in zip(topic_parts, pattern_parts):
            if pattern_part not in ['+', '*'] and pattern_part != topic_part:
                return False

        return True

    async def _handle_telemetry_data(self, topic: str, payload: str) -> None:
        """Handle telemetry data messages."""
        try:
            # Extract device ID from topic
            device_id = self._extract_device_id(topic)
            if not device_id:
                logger.warning(f"Could not extract device ID from topic: {topic}")
                return

            # Parse JSON payload
            try:
                data = json.loads(payload)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in telemetry message: {e}")
                return

            # Validate data structure
            if not isinstance(data, dict):
                logger.error("Telemetry data must be a JSON object")
                return

            # Extract readings and timestamp
            readings = data.get('readings', {})
            timestamp_str = data.get('timestamp')

            # Parse timestamp if provided
            timestamp = None
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Invalid timestamp format: {timestamp_str}")

            # Write telemetry data
            if self.telemetry_service and readings:
                await self.telemetry_service.write_telemetry_reading(
                    device_id=UUID(device_id),
                    readings=readings,
                    timestamp=timestamp
                )

                logger.debug(f"Processed telemetry data for device {device_id}")

        except Exception as e:
            logger.error(f"Error handling telemetry data: {e}")

    async def _handle_device_status(self, topic: str, payload: str) -> None:
        """Handle device status messages."""
        try:
            # Extract device ID from topic
            device_id = self._extract_device_id(topic)
            if not device_id:
                logger.warning(f"Could not extract device ID from topic: {topic}")
                return

            # Parse status payload
            try:
                data = json.loads(payload)
                status_str = data.get('status', payload.strip())
            except json.JSONDecodeError:
                status_str = payload.strip()

            # Map status string to enum
            status_mapping = {
                'online': DeviceStatus.ONLINE,
                'offline': DeviceStatus.OFFLINE,
                'maintenance': DeviceStatus.MAINTENANCE
            }

            status = status_mapping.get(status_str.lower())
            if not status:
                logger.warning(f"Unknown device status: {status_str}")
                return

            # Update device status
            if self.device_service:
                await self.device_service.update_device_status(
                    device_id=UUID(device_id),
                    status=status,
                    update_last_seen=True
                )

                logger.debug(f"Updated device {device_id} status to {status.value}")

        except Exception as e:
            logger.error(f"Error handling device status: {e}")

    async def _handle_device_heartbeat(self, topic: str, payload: str) -> None:
        """Handle device heartbeat messages."""
        try:
            # Extract device ID from topic
            device_id = self._extract_device_id(topic)
            if not device_id:
                logger.warning(f"Could not extract device ID from topic: {topic}")
                return

            # Update device last seen
            if self.device_service:
                await self.device_service.update_device_status(
                    device_id=UUID(device_id),
                    status=DeviceStatus.ONLINE,
                    update_last_seen=True
                )

                logger.debug(f"Processed heartbeat for device {device_id}")

        except Exception as e:
            logger.error(f"Error handling device heartbeat: {e}")

    def _extract_device_id(self, topic: str) -> Optional[str]:
        """Extract device ID from MQTT topic."""
        try:
            # Assuming topic format: telemetry/{device_id}/{message_type}
            parts = topic.split('/')
            if len(parts) >= 2:
                return parts[1]
        except Exception:
            pass
        return None

    async def publish_message(
        self,
        topic: str,
        payload: Any,
        qos: int = 1,
        retain: bool = False
    ) -> None:
        """
        Publish message to MQTT topic.

        Args:
            topic: MQTT topic
            payload: Message payload (will be JSON encoded if not string)
            qos: Quality of Service level
            retain: Retain flag

        Raises:
            HTTPException: If publish fails
        """
        try:
            if not self._client or not self._running:
                raise HTTPException(
                    status_code=503,
                    detail="MQTT service not available"
                )

            # Convert payload to string if needed
            if isinstance(payload, (dict, list)):
                payload_str = json.dumps(payload)
            else:
                payload_str = str(payload)

            await self._client.publish(
                topic=topic,
                payload=payload_str,
                qos=qos,
                retain=retain
            )

            logger.debug(f"Published MQTT message to topic {topic}")

        except Exception as e:
            logger.error(f"Failed to publish MQTT message: {e}")
            raise HTTPException(
                status_code=500,
                detail="Failed to publish MQTT message"
            )

    def add_message_handler(self, topic_pattern: str, handler: Callable) -> None:
        """
        Add custom message handler for topic pattern.

        Args:
            topic_pattern: MQTT topic pattern (supports + and * wildcards)
            handler: Async handler function that accepts (topic, payload)
        """
        self._message_handlers[topic_pattern] = handler
        logger.debug(f"Added MQTT message handler for pattern: {topic_pattern}")

    def remove_message_handler(self, topic_pattern: str) -> None:
        """
        Remove message handler for topic pattern.

        Args:
            topic_pattern: MQTT topic pattern to remove
        """
        if topic_pattern in self._message_handlers:
            del self._message_handlers[topic_pattern]
            logger.debug(f"Removed MQTT message handler for pattern: {topic_pattern}")

    @property
    def is_connected(self) -> bool:
        """Check if MQTT client is connected."""
        return self._client is not None and self._running

    async def get_status(self) -> Dict[str, Any]:
        """
        Get MQTT service status.

        Returns:
            Dictionary with service status information
        """
        return {
            'connected': self.is_connected,
            'broker_host': self.broker_host,
            'broker_port': self.broker_port,
            'reconnect_attempts': self._reconnect_attempts,
            'subscribed_topics': [
                self.telemetry_topic,
                self.status_topic,
                self.heartbeat_topic
            ],
            'message_handlers': list(self._message_handlers.keys())
        }


# Global service instance
mqtt_service: Optional[MQTTService] = None


async def get_mqtt_service() -> MQTTService:
    """
    Dependency function to get MQTT service instance.

    Returns:
        MQTT service instance

    Raises:
        HTTPException: If service not initialized
    """
    global mqtt_service

    if mqtt_service is None:
        raise HTTPException(
            status_code=500,
            detail="MQTT service not initialized"
        )

    return mqtt_service


async def initialize_mqtt_service(
    broker_host: str,
    broker_port: int = 1883,
    username: Optional[str] = None,
    password: Optional[str] = None,
    telemetry_service: Optional[TelemetryService] = None,
    device_service: Optional[DeviceService] = None
) -> MQTTService:
    """
    Initialize global MQTT service instance.

    Args:
        broker_host: MQTT broker hostname
        broker_port: MQTT broker port
        username: Optional MQTT username
        password: Optional MQTT password
        telemetry_service: Telemetry service for data processing
        device_service: Device service for status updates

    Returns:
        Initialized MQTT service
    """
    global mqtt_service

    mqtt_service = MQTTService(
        broker_host=broker_host,
        broker_port=broker_port,
        username=username,
        password=password,
        telemetry_service=telemetry_service,
        device_service=device_service
    )

    await mqtt_service.initialize()
    return mqtt_service


async def close_mqtt_service() -> None:
    """Close global MQTT service instance."""
    global mqtt_service

    if mqtt_service:
        await mqtt_service.close()
        mqtt_service = None