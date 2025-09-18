"""
MQTT message parser and validator service.

Handles parsing and validation of incoming MQTT messages from IoT devices,
ensuring data integrity and proper format before forwarding to data pipeline.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

import jsonschema
from pydantic import BaseModel, ValidationError, validator

# Setup logging
logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Supported MQTT message types."""
    TELEMETRY = "telemetry"
    STATUS = "status"
    HEARTBEAT = "heartbeat"
    ALERT = "alert"
    COMMAND_RESPONSE = "command_response"


class TelemetryType(str, Enum):
    """Supported telemetry field types."""
    TEMPERATURE = "temperature"
    VIBRATION = "vibration"
    POWER = "power"
    ELECTRICITY = "electricity"
    PRESSURE = "pressure"
    HUMIDITY = "humidity"


@dataclass
class ValidationResult:
    """Result of message validation."""
    is_valid: bool
    parsed_data: Optional[Dict[str, Any]] = None
    errors: List[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class TelemetryReading(BaseModel):
    """Individual telemetry reading model."""
    field_name: str
    value: Union[float, int]
    unit: str
    timestamp: Optional[datetime] = None
    quality: Optional[float] = None  # Data quality indicator (0-1)

    @validator('field_name')
    def validate_field_name(cls, v):
        """Validate telemetry field name."""
        valid_fields = [t.value for t in TelemetryType]
        if v not in valid_fields:
            logger.warning(f"Unknown telemetry field: {v}")
        return v

    @validator('value')
    def validate_value_range(cls, v, values):
        """Validate value ranges based on field type."""
        field_name = values.get('field_name')

        # Define reasonable ranges for each field type
        ranges = {
            'temperature': (-100, 200),  # Celsius
            'vibration': (0, 100),       # mm/s
            'power': (0, 100000),        # Watts
            'electricity': (0, 1000000), # kWh
            'pressure': (0, 10000),      # kPa
            'humidity': (0, 100)         # %
        }

        if field_name in ranges:
            min_val, max_val = ranges[field_name]
            if not (min_val <= v <= max_val):
                raise ValueError(f"Value {v} out of range [{min_val}, {max_val}] for {field_name}")

        return v

    @validator('quality')
    def validate_quality(cls, v):
        """Validate quality indicator."""
        if v is not None and not (0 <= v <= 1):
            raise ValueError("Quality must be between 0 and 1")
        return v


class TelemetryMessage(BaseModel):
    """Complete telemetry message model."""
    message_type: MessageType
    device_id: str
    timestamp: datetime
    readings: List[TelemetryReading]
    sequence_number: Optional[int] = None
    batch_id: Optional[str] = None

    @validator('device_id')
    def validate_device_id(cls, v):
        """Validate device ID format."""
        if not v or len(v) < 3:
            raise ValueError("Device ID must be at least 3 characters")
        return v

    @validator('readings')
    def validate_readings_not_empty(cls, v):
        """Ensure readings list is not empty."""
        if not v:
            raise ValueError("Readings list cannot be empty")
        return v


class StatusMessage(BaseModel):
    """Device status message model."""
    message_type: MessageType
    device_id: str
    timestamp: datetime
    status: str
    battery_level: Optional[float] = None
    signal_strength: Optional[float] = None
    firmware_version: Optional[str] = None
    uptime_seconds: Optional[int] = None

    @validator('status')
    def validate_status(cls, v):
        """Validate status values."""
        valid_statuses = ['online', 'offline', 'maintenance', 'error', 'warning']
        if v not in valid_statuses:
            raise ValueError(f"Invalid status: {v}")
        return v

    @validator('battery_level')
    def validate_battery_level(cls, v):
        """Validate battery level percentage."""
        if v is not None and not (0 <= v <= 100):
            raise ValueError("Battery level must be between 0 and 100")
        return v


class HeartbeatMessage(BaseModel):
    """Device heartbeat message model."""
    message_type: MessageType
    device_id: str
    timestamp: datetime
    sequence_number: int
    system_health: Optional[Dict[str, Any]] = None


class AlertMessage(BaseModel):
    """Device alert message model."""
    message_type: MessageType
    device_id: str
    timestamp: datetime
    alert_type: str
    severity: str
    description: str
    alert_code: Optional[str] = None
    acknowledgment_required: bool = False

    @validator('severity')
    def validate_severity(cls, v):
        """Validate alert severity."""
        valid_severities = ['info', 'warning', 'error', 'critical']
        if v not in valid_severities:
            raise ValueError(f"Invalid severity: {v}")
        return v


class MQTTMessageParser:
    """MQTT message parser and validator."""

    def __init__(self):
        """Initialize the parser."""
        self.message_models = {
            MessageType.TELEMETRY: TelemetryMessage,
            MessageType.STATUS: StatusMessage,
            MessageType.HEARTBEAT: HeartbeatMessage,
            MessageType.ALERT: AlertMessage,
        }

    def parse_topic(self, topic: str) -> Dict[str, str]:
        """
        Parse MQTT topic to extract routing information.

        Expected format: iot/{organization_slug}/{site_slug}/{area_slug}/{device_id}/{message_type}
        """
        try:
            parts = topic.split('/')
            if len(parts) < 6 or parts[0] != 'iot':
                raise ValueError(f"Invalid topic format: {topic}")

            return {
                'organization_slug': parts[1],
                'site_slug': parts[2],
                'area_slug': parts[3],
                'device_id': parts[4],
                'message_type': parts[5]
            }
        except Exception as e:
            logger.error(f"Failed to parse topic {topic}: {e}")
            raise ValueError(f"Invalid topic format: {topic}")

    def parse_payload(self, payload: Union[str, bytes]) -> Dict[str, Any]:
        """Parse JSON payload from MQTT message."""
        try:
            if isinstance(payload, bytes):
                payload = payload.decode('utf-8')

            return json.loads(payload)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON payload: {e}")
            raise ValueError(f"Invalid JSON payload: {e}")
        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode payload: {e}")
            raise ValueError(f"Failed to decode payload: {e}")

    def validate_message(self, topic: str, payload: Union[str, bytes]) -> ValidationResult:
        """
        Validate complete MQTT message.

        Args:
            topic: MQTT topic string
            payload: Message payload (JSON string or bytes)

        Returns:
            ValidationResult with validation status and parsed data
        """
        result = ValidationResult(is_valid=False)

        try:
            # Parse topic
            topic_info = self.parse_topic(topic)

            # Parse payload
            payload_data = self.parse_payload(payload)

            # Get message type
            message_type = topic_info.get('message_type')
            if message_type not in [t.value for t in MessageType]:
                result.errors.append(f"Unknown message type: {message_type}")
                return result

            # Add device_id from topic if not in payload
            if 'device_id' not in payload_data:
                payload_data['device_id'] = topic_info['device_id']

            # Add message_type if not in payload
            if 'message_type' not in payload_data:
                payload_data['message_type'] = message_type

            # Add timestamp if not provided
            if 'timestamp' not in payload_data:
                payload_data['timestamp'] = datetime.utcnow()
                result.warnings.append("Timestamp not provided, using current time")

            # Validate using appropriate model
            message_type_enum = MessageType(message_type)
            model_class = self.message_models.get(message_type_enum)

            if not model_class:
                result.errors.append(f"No model defined for message type: {message_type}")
                return result

            # Validate with Pydantic model
            validated_message = model_class(**payload_data)

            # Prepare result
            result.is_valid = True
            result.parsed_data = {
                'topic_info': topic_info,
                'message': validated_message.dict(),
                'raw_payload': payload_data
            }

            logger.debug(f"Successfully validated message from {topic_info['device_id']}")

        except ValidationError as e:
            result.errors.extend([f"Validation error: {error['msg']}" for error in e.errors()])
            logger.warning(f"Validation failed for topic {topic}: {e}")
        except ValueError as e:
            result.errors.append(str(e))
            logger.warning(f"Value error for topic {topic}: {e}")
        except Exception as e:
            result.errors.append(f"Unexpected error: {str(e)}")
            logger.error(f"Unexpected error parsing message from {topic}: {e}")

        return result

    def validate_batch_messages(self, messages: List[tuple]) -> List[ValidationResult]:
        """
        Validate a batch of MQTT messages.

        Args:
            messages: List of (topic, payload) tuples

        Returns:
            List of ValidationResult objects
        """
        results = []

        for topic, payload in messages:
            try:
                result = self.validate_message(topic, payload)
                results.append(result)
            except Exception as e:
                error_result = ValidationResult(
                    is_valid=False,
                    errors=[f"Failed to process message: {str(e)}"]
                )
                results.append(error_result)
                logger.error(f"Failed to validate message: {e}")

        return results

    def extract_telemetry_data(self, validation_result: ValidationResult) -> Optional[Dict[str, Any]]:
        """
        Extract telemetry data for database insertion.

        Args:
            validation_result: Validated message result

        Returns:
            Structured telemetry data or None if not applicable
        """
        if not validation_result.is_valid:
            return None

        message_data = validation_result.parsed_data['message']
        topic_info = validation_result.parsed_data['topic_info']

        if message_data['message_type'] != MessageType.TELEMETRY:
            return None

        # Structure data for InfluxDB
        telemetry_data = {
            'measurement': 'device_telemetry',
            'tags': {
                'device_id': message_data['device_id'],
                'organization': topic_info['organization_slug'],
                'site': topic_info['site_slug'],
                'area': topic_info['area_slug']
            },
            'timestamp': message_data['timestamp'],
            'fields': {}
        }

        # Add telemetry readings as fields
        for reading in message_data['readings']:
            field_name = reading['field_name']
            telemetry_data['fields'][f"{field_name}_value"] = reading['value']
            telemetry_data['fields'][f"{field_name}_unit"] = reading['unit']

            if reading.get('quality') is not None:
                telemetry_data['fields'][f"{field_name}_quality"] = reading['quality']

        # Add sequence number if available
        if message_data.get('sequence_number'):
            telemetry_data['fields']['sequence_number'] = message_data['sequence_number']

        return telemetry_data

    def get_validation_stats(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """
        Generate validation statistics from results.

        Args:
            results: List of validation results

        Returns:
            Statistics dictionary
        """
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)
        invalid = total - valid

        error_counts = {}
        warning_counts = {}

        for result in results:
            for error in result.errors:
                error_counts[error] = error_counts.get(error, 0) + 1
            for warning in result.warnings:
                warning_counts[warning] = warning_counts.get(warning, 0) + 1

        return {
            'total_messages': total,
            'valid_messages': valid,
            'invalid_messages': invalid,
            'success_rate': valid / total if total > 0 else 0,
            'error_counts': error_counts,
            'warning_counts': warning_counts
        }


# Global parser instance
mqtt_parser = MQTTMessageParser()


def parse_mqtt_message(topic: str, payload: Union[str, bytes]) -> ValidationResult:
    """
    Convenience function to parse and validate an MQTT message.

    Args:
        topic: MQTT topic string
        payload: Message payload

    Returns:
        ValidationResult
    """
    return mqtt_parser.validate_message(topic, payload)


def extract_telemetry(validation_result: ValidationResult) -> Optional[Dict[str, Any]]:
    """
    Convenience function to extract telemetry data.

    Args:
        validation_result: Validated message result

    Returns:
        Telemetry data or None
    """
    return mqtt_parser.extract_telemetry_data(validation_result)