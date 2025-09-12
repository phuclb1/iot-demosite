"""Async MQTT client for IoT telemetry data ingestion."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Callable

import asyncio_mqtt as mqtt
from pydantic import BaseModel, ValidationError

from src.config import settings
from src.database.influxdb import influxdb_manager

logger = logging.getLogger(__name__)


class TelemetryMessage(BaseModel):
    """Telemetry message schema validation."""
    
    timestamp: datetime
    vibration: float
    temperature: float
    power: float
    electricity: float


class MQTTClient:
    """Async MQTT client for telemetry data ingestion."""

    def __init__(self):
        self._client: Optional[mqtt.Client] = None
        self._running = False
        self._message_handler: Optional[Callable] = None

    async def connect(self) -> None:
        """Connect to MQTT broker."""
        try:
            self._client = mqtt.Client(
                hostname=settings.mqtt_broker_host,
                port=settings.mqtt_broker_port,
                username=settings.mqtt_username,
                password=settings.mqtt_password,
                keepalive=60,
                clean_session=True,
            )
            
            # Test connection
            await self._client.__aenter__()
            logger.info(
                f"Connected to MQTT broker: {settings.mqtt_broker_host}:{settings.mqtt_broker_port}"
            )
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        if self._client:
            try:
                await self._client.__aexit__(None, None, None)
                logger.info("Disconnected from MQTT broker")
            except Exception as e:
                logger.warning(f"Error during MQTT disconnect: {e}")
            finally:
                self._client = None
                self._running = False

    async def subscribe_to_telemetry(self) -> None:
        """Subscribe to telemetry topics and start processing messages."""
        if not self._client:
            raise RuntimeError("MQTT client not connected. Call connect() first.")

        try:
            # Subscribe to telemetry topic pattern: iot/+/+/+/+/telemetry/v1
            topic_pattern = settings.mqtt_topic_pattern
            await self._client.subscribe(topic_pattern)
            logger.info(f"Subscribed to MQTT topic pattern: {topic_pattern}")

            self._running = True
            
            # Start message processing loop
            async for message in self._client.messages:
                if not self._running:
                    break
                    
                try:
                    await self._process_telemetry_message(message)
                except Exception as e:
                    logger.error(f"Error processing MQTT message: {e}")
                    
        except Exception as e:
            logger.error(f"Error in MQTT subscription: {e}")
            raise

    async def _process_telemetry_message(self, message: mqtt.MqttMessage) -> None:
        """Process incoming telemetry message."""
        try:
            # Parse topic to extract device hierarchy
            # Topic format: iot/{org}/{site}/{area}/{device_id}/telemetry/v1
            topic_parts = message.topic.value.split('/')
            
            if len(topic_parts) != 7 or topic_parts[0] != 'iot' or topic_parts[5] != 'telemetry':
                logger.warning(f"Invalid topic format: {message.topic.value}")
                return

            organization = topic_parts[1]
            site = topic_parts[2]
            area = topic_parts[3]
            device_id = topic_parts[4]

            # Parse message payload
            try:
                payload = json.loads(message.payload.decode())
                telemetry_data = TelemetryMessage(**payload)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Invalid telemetry message format from {device_id}: {e}")
                return

            # Store telemetry data in InfluxDB
            await influxdb_manager.write_telemetry_data(
                device_id=device_id,
                organization=organization,
                site=site,
                area=area,
                timestamp=telemetry_data.timestamp,
                vibration=telemetry_data.vibration,
                temperature=telemetry_data.temperature,
                power=telemetry_data.power,
                electricity=telemetry_data.electricity,
            )

            logger.debug(
                f"Processed telemetry data from {organization}/{site}/{area}/{device_id}"
            )

            # Call custom message handler if set
            if self._message_handler:
                await self._message_handler({
                    "device_id": device_id,
                    "organization": organization,
                    "site": site,
                    "area": area,
                    "timestamp": telemetry_data.timestamp,
                    "vibration": telemetry_data.vibration,
                    "temperature": telemetry_data.temperature,
                    "power": telemetry_data.power,
                    "electricity": telemetry_data.electricity,
                })

        except Exception as e:
            logger.error(f"Failed to process telemetry message: {e}")
            raise

    async def publish_message(
        self, 
        topic: str, 
        payload: Dict[str, Any], 
        qos: int = 1
    ) -> None:
        """Publish a message to MQTT topic."""
        if not self._client:
            raise RuntimeError("MQTT client not connected. Call connect() first.")

        try:
            message_payload = json.dumps(payload, default=str)
            await self._client.publish(topic, message_payload, qos=qos)
            logger.debug(f"Published message to topic {topic}")
        except Exception as e:
            logger.error(f"Failed to publish message to {topic}: {e}")
            raise

    def set_message_handler(self, handler: Callable) -> None:
        """Set custom message handler for processed telemetry data."""
        self._message_handler = handler

    async def stop(self) -> None:
        """Stop the MQTT client."""
        self._running = False
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        """Check if MQTT client is connected."""
        return self._client is not None and self._running


# Global MQTT client instance
mqtt_client = MQTTClient()


async def init_mqtt() -> None:
    """Initialize MQTT client connection."""
    await mqtt_client.connect()


async def close_mqtt() -> None:
    """Close MQTT client connection."""
    await mqtt_client.disconnect()


async def start_telemetry_ingestion() -> None:
    """Start telemetry data ingestion from MQTT."""
    try:
        await mqtt_client.subscribe_to_telemetry()
    except Exception as e:
        logger.error(f"Failed to start telemetry ingestion: {e}")
        raise


def get_mqtt_client() -> MQTTClient:
    """Get the MQTT client instance."""
    return mqtt_client