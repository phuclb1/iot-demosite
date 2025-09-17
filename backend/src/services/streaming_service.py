"""
Real-time streaming service using Server-Sent Events (SSE).

Provides real-time telemetry data streaming to web clients with filtering,
subscription management, and connection handling.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, Set, List, AsyncGenerator
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from fastapi import HTTPException, Depends
from fastapi.responses import StreamingResponse

from ..services.telemetry_service import get_telemetry_service, TelemetryService
from ..services.mqtt_service import get_mqtt_service, MQTTService
from ..models.telemetry_reading import TelemetryField


logger = logging.getLogger(__name__)


class StreamType(str, Enum):
    """Types of data streams."""
    TELEMETRY = "telemetry"
    DEVICE_STATUS = "device_status"
    ALERTS = "alerts"


@dataclass
class StreamSubscription:
    """Stream subscription configuration."""
    stream_type: StreamType
    device_ids: Optional[Set[UUID]] = None
    fields: Optional[Set[TelemetryField]] = None
    organization_id: Optional[UUID] = None
    site_id: Optional[UUID] = None
    area_id: Optional[UUID] = None


@dataclass
class StreamMessage:
    """Stream message format."""
    event_type: str
    data: Dict[str, Any]
    timestamp: datetime
    id: Optional[str] = None


class StreamingService:
    """Service for real-time data streaming via SSE."""

    def __init__(self, telemetry_service: TelemetryService, mqtt_service: MQTTService):
        """
        Initialize streaming service.

        Args:
            telemetry_service: Telemetry service for data queries
            mqtt_service: MQTT service for real-time updates
        """
        self.telemetry_service = telemetry_service
        self.mqtt_service = mqtt_service

        # Connection management
        self._active_streams: Dict[str, Dict[str, Any]] = {}
        self._stream_queues: Dict[str, asyncio.Queue] = {}
        self._subscription_handlers: Dict[str, StreamSubscription] = {}

        # Message buffer for new connections
        self._message_buffer: Dict[str, List[StreamMessage]] = {}
        self._buffer_size = 100

        # Stream ID counter
        self._stream_counter = 0
        self._lock = asyncio.Lock()

    async def create_stream(
        self,
        subscription: StreamSubscription,
        client_id: Optional[str] = None
    ) -> str:
        """
        Create new SSE stream.

        Args:
            subscription: Stream subscription configuration
            client_id: Optional client identifier

        Returns:
            Stream ID for the created stream
        """
        async with self._lock:
            self._stream_counter += 1
            stream_id = f"stream_{self._stream_counter}_{client_id or 'anonymous'}"

        # Create queue for this stream
        queue = asyncio.Queue(maxsize=1000)
        self._stream_queues[stream_id] = queue
        self._subscription_handlers[stream_id] = subscription

        # Initialize stream info
        self._active_streams[stream_id] = {
            'created_at': datetime.utcnow(),
            'subscription': subscription,
            'client_id': client_id,
            'message_count': 0
        }

        logger.info(f"Created stream {stream_id} for {subscription.stream_type}")
        return stream_id

    async def close_stream(self, stream_id: str) -> None:
        """
        Close SSE stream and cleanup resources.

        Args:
            stream_id: Stream identifier
        """
        # Remove from active streams
        if stream_id in self._active_streams:
            del self._active_streams[stream_id]

        # Close queue
        if stream_id in self._stream_queues:
            queue = self._stream_queues[stream_id]
            # Put sentinel value to signal stream end
            try:
                await queue.put(None)
            except:
                pass
            del self._stream_queues[stream_id]

        # Remove subscription handler
        if stream_id in self._subscription_handlers:
            del self._subscription_handlers[stream_id]

        # Clear message buffer
        if stream_id in self._message_buffer:
            del self._message_buffer[stream_id]

        logger.info(f"Closed stream {stream_id}")

    async def generate_stream(self, stream_id: str) -> AsyncGenerator[str, None]:
        """
        Generate SSE stream data.

        Args:
            stream_id: Stream identifier

        Yields:
            SSE formatted messages
        """
        try:
            if stream_id not in self._stream_queues:
                yield self._format_sse_message("error", {"message": "Stream not found"})
                return

            queue = self._stream_queues[stream_id]
            subscription = self._subscription_handlers[stream_id]

            # Send initial connection message
            yield self._format_sse_message(
                "connected",
                {
                    "stream_id": stream_id,
                    "stream_type": subscription.stream_type.value,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

            # Send buffered messages if any
            if stream_id in self._message_buffer:
                for message in self._message_buffer[stream_id]:
                    yield self._format_sse_message(
                        message.event_type,
                        message.data,
                        message.id
                    )

            # Stream real-time messages
            while True:
                try:
                    # Wait for message with timeout
                    message = await asyncio.wait_for(queue.get(), timeout=30.0)

                    # Check for stream end sentinel
                    if message is None:
                        break

                    # Send message
                    yield self._format_sse_message(
                        message.event_type,
                        message.data,
                        message.id
                    )

                    # Update message count
                    if stream_id in self._active_streams:
                        self._active_streams[stream_id]['message_count'] += 1

                except asyncio.TimeoutError:
                    # Send keepalive message
                    yield self._format_sse_message(
                        "keepalive",
                        {"timestamp": datetime.utcnow().isoformat()}
                    )

        except Exception as e:
            logger.error(f"Error in stream {stream_id}: {e}")
            yield self._format_sse_message("error", {"message": str(e)})

        finally:
            # Cleanup
            await self.close_stream(stream_id)

    async def broadcast_message(
        self,
        event_type: str,
        data: Dict[str, Any],
        filter_subscription: Optional[StreamSubscription] = None
    ) -> int:
        """
        Broadcast message to matching streams.

        Args:
            event_type: Type of event
            data: Message data
            filter_subscription: Optional filter for matching streams

        Returns:
            Number of streams that received the message
        """
        message = StreamMessage(
            event_type=event_type,
            data=data,
            timestamp=datetime.utcnow(),
            id=f"{event_type}_{int(datetime.utcnow().timestamp() * 1000)}"
        )

        broadcast_count = 0

        for stream_id, queue in self._stream_queues.items():
            subscription = self._subscription_handlers.get(stream_id)

            if subscription and self._message_matches_subscription(message, subscription, filter_subscription):
                try:
                    # Add to queue (non-blocking)
                    queue.put_nowait(message)
                    broadcast_count += 1

                    # Add to buffer for new connections
                    if stream_id not in self._message_buffer:
                        self._message_buffer[stream_id] = []

                    self._message_buffer[stream_id].append(message)

                    # Trim buffer if too large
                    if len(self._message_buffer[stream_id]) > self._buffer_size:
                        self._message_buffer[stream_id] = self._message_buffer[stream_id][-self._buffer_size:]

                except asyncio.QueueFull:
                    logger.warning(f"Queue full for stream {stream_id}, dropping message")
                except Exception as e:
                    logger.error(f"Error broadcasting to stream {stream_id}: {e}")

        logger.debug(f"Broadcasted {event_type} message to {broadcast_count} streams")
        return broadcast_count

    async def broadcast_telemetry_update(
        self,
        device_id: UUID,
        readings: Dict[str, float],
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Broadcast telemetry update to interested streams.

        Args:
            device_id: Device UUID
            readings: Telemetry readings
            timestamp: Optional timestamp
        """
        data = {
            "device_id": str(device_id),
            "readings": readings,
            "timestamp": (timestamp or datetime.utcnow()).isoformat()
        }

        # Create filter for device-specific streams
        filter_sub = StreamSubscription(
            stream_type=StreamType.TELEMETRY,
            device_ids={device_id}
        )

        await self.broadcast_message("telemetry_update", data, filter_sub)

    async def broadcast_device_status_update(
        self,
        device_id: UUID,
        status: str,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Broadcast device status update to interested streams.

        Args:
            device_id: Device UUID
            status: New device status
            timestamp: Optional timestamp
        """
        data = {
            "device_id": str(device_id),
            "status": status,
            "timestamp": (timestamp or datetime.utcnow()).isoformat()
        }

        # Create filter for device-specific streams
        filter_sub = StreamSubscription(
            stream_type=StreamType.DEVICE_STATUS,
            device_ids={device_id}
        )

        await self.broadcast_message("device_status_update", data, filter_sub)

    def _message_matches_subscription(
        self,
        message: StreamMessage,
        subscription: StreamSubscription,
        filter_subscription: Optional[StreamSubscription] = None
    ) -> bool:
        """
        Check if message matches subscription criteria.

        Args:
            message: Stream message
            subscription: Stream subscription
            filter_subscription: Optional additional filter

        Returns:
            True if message matches subscription
        """
        # Apply filter subscription if provided
        if filter_subscription:
            # Check stream type match
            if subscription.stream_type != filter_subscription.stream_type:
                return False

            # Check device ID match
            if filter_subscription.device_ids:
                device_id_str = message.data.get('device_id')
                if device_id_str:
                    try:
                        device_id = UUID(device_id_str)
                        if subscription.device_ids and device_id not in subscription.device_ids:
                            return False
                        if device_id not in filter_subscription.device_ids:
                            return False
                    except ValueError:
                        return False

        # Check stream type
        if message.event_type.startswith('telemetry') and subscription.stream_type != StreamType.TELEMETRY:
            return False
        if message.event_type.startswith('device_status') and subscription.stream_type != StreamType.DEVICE_STATUS:
            return False

        # Check device ID filter
        if subscription.device_ids:
            device_id_str = message.data.get('device_id')
            if device_id_str:
                try:
                    device_id = UUID(device_id_str)
                    if device_id not in subscription.device_ids:
                        return False
                except ValueError:
                    return False

        # Check field filter for telemetry
        if subscription.fields and message.event_type == 'telemetry_update':
            readings = message.data.get('readings', {})
            field_names = set(readings.keys())
            subscription_field_names = {field.value for field in subscription.fields}
            if not field_names.intersection(subscription_field_names):
                return False

        return True

    def _format_sse_message(
        self,
        event_type: str,
        data: Dict[str, Any],
        message_id: Optional[str] = None
    ) -> str:
        """
        Format message as SSE.

        Args:
            event_type: Event type
            data: Message data
            message_id: Optional message ID

        Returns:
            SSE formatted message string
        """
        lines = []

        if message_id:
            lines.append(f"id: {message_id}")

        lines.append(f"event: {event_type}")
        lines.append(f"data: {json.dumps(data)}")
        lines.append("")  # Empty line to end message

        return "\n".join(lines) + "\n"

    async def get_active_streams(self) -> Dict[str, Any]:
        """
        Get information about active streams.

        Returns:
            Dictionary with active stream information
        """
        stream_info = {}

        for stream_id, stream_data in self._active_streams.items():
            subscription = stream_data['subscription']

            stream_info[stream_id] = {
                'created_at': stream_data['created_at'].isoformat(),
                'client_id': stream_data['client_id'],
                'message_count': stream_data['message_count'],
                'stream_type': subscription.stream_type.value,
                'device_count': len(subscription.device_ids) if subscription.device_ids else 0,
                'field_count': len(subscription.fields) if subscription.fields else 0,
                'queue_size': self._stream_queues[stream_id].qsize() if stream_id in self._stream_queues else 0
            }

        return {
            'active_stream_count': len(stream_info),
            'streams': stream_info
        }

    async def create_telemetry_stream_response(
        self,
        device_ids: Optional[List[UUID]] = None,
        fields: Optional[List[TelemetryField]] = None,
        organization_id: Optional[UUID] = None,
        site_id: Optional[UUID] = None,
        area_id: Optional[UUID] = None,
        client_id: Optional[str] = None
    ) -> StreamingResponse:
        """
        Create SSE streaming response for telemetry data.

        Args:
            device_ids: Optional list of device IDs to filter
            fields: Optional list of telemetry fields to include
            organization_id: Optional organization filter
            site_id: Optional site filter
            area_id: Optional area filter
            client_id: Optional client identifier

        Returns:
            FastAPI StreamingResponse for SSE
        """
        # Create subscription
        subscription = StreamSubscription(
            stream_type=StreamType.TELEMETRY,
            device_ids=set(device_ids) if device_ids else None,
            fields=set(fields) if fields else None,
            organization_id=organization_id,
            site_id=site_id,
            area_id=area_id
        )

        # Create stream
        stream_id = await self.create_stream(subscription, client_id)

        # Return streaming response
        return StreamingResponse(
            self.generate_stream(stream_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )


# Global service instance
streaming_service: Optional[StreamingService] = None


async def get_streaming_service(
    telemetry_service: TelemetryService = Depends(get_telemetry_service),
    mqtt_service: MQTTService = Depends(get_mqtt_service)
) -> StreamingService:
    """
    Dependency function to get streaming service instance.

    Args:
        telemetry_service: Telemetry service
        mqtt_service: MQTT service

    Returns:
        Streaming service instance
    """
    global streaming_service

    if streaming_service is None:
        streaming_service = StreamingService(telemetry_service, mqtt_service)

    return streaming_service