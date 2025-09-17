"""
Telemetry API endpoints.

Provides REST API endpoints for telemetry data retrieval including
current readings, historical data, and real-time streaming.
"""

import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse

from ...models.telemetry_reading import TelemetryField, AggregationInterval
from ...models.user import UserResponse
from ...services.telemetry_service import get_telemetry_service, TelemetryService
from ...services.streaming_service import get_streaming_service, StreamingService
from ...middleware.auth_middleware import require_viewer_role


logger = logging.getLogger(__name__)

# Create router for telemetry
router = APIRouter(prefix="/telemetry", tags=["telemetry"])


@router.get(
    "/current/{device_id}",
    summary="Get current telemetry readings",
    description="Get the latest telemetry readings for a device."
)
async def get_current_telemetry(
    device_id: UUID,
    fields: Optional[List[TelemetryField]] = Query(None, description="Specific telemetry fields to retrieve"),
    current_user: UserResponse = Depends(require_viewer_role),
    telemetry_service: TelemetryService = Depends(get_telemetry_service)
):
    """
    Get current (latest) telemetry readings for a device.

    Returns the most recent telemetry data for the specified device.
    User must have access to the organization containing the device.
    """
    try:
        # TODO: Add device access validation through hierarchy
        # For now, we'll validate device existence in the service

        current_telemetry = await telemetry_service.get_current_telemetry(
            device_id=device_id,
            fields=fields
        )

        logger.info(f"Retrieved current telemetry for device {device_id}")
        return current_telemetry

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting current telemetry for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve current telemetry"
        )


@router.get(
    "/historical/{device_id}",
    summary="Get historical telemetry data",
    description="Get historical telemetry data for a device within a time range."
)
async def get_historical_telemetry(
    device_id: UUID,
    start_time: datetime = Query(..., description="Start time for historical data query"),
    end_time: datetime = Query(..., description="End time for historical data query"),
    fields: Optional[List[TelemetryField]] = Query(None, description="Specific telemetry fields to retrieve"),
    interval: Optional[AggregationInterval] = Query(None, description="Aggregation interval for data points"),
    limit: Optional[int] = Query(None, ge=1, le=10000, description="Maximum number of data points to return"),
    current_user: UserResponse = Depends(require_viewer_role),
    telemetry_service: TelemetryService = Depends(get_telemetry_service)
):
    """
    Get historical telemetry data for a device within a time range.

    Supports time range filtering, field selection, aggregation intervals, and result limiting.
    User must have access to the organization containing the device.
    """
    try:
        # Validate time range
        if start_time >= end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start time must be before end time"
            )

        # Check time range isn't too large (max 30 days)
        time_diff = end_time - start_time
        if time_diff.days > 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Time range cannot exceed 30 days"
            )

        historical_telemetry = await telemetry_service.get_historical_telemetry(
            device_id=device_id,
            start_time=start_time,
            end_time=end_time,
            fields=fields,
            interval=interval,
            limit=limit
        )

        logger.info(f"Retrieved historical telemetry for device {device_id}")
        return historical_telemetry

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting historical telemetry for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve historical telemetry"
        )


@router.get(
    "/aggregated/{device_id}",
    summary="Get aggregated telemetry data",
    description="Get aggregated telemetry statistics for a specific field and time range."
)
async def get_aggregated_telemetry(
    device_id: UUID,
    field: TelemetryField = Query(..., description="Telemetry field to aggregate"),
    start_time: datetime = Query(..., description="Start time for aggregation query"),
    end_time: datetime = Query(..., description="End time for aggregation query"),
    interval: AggregationInterval = Query(..., description="Aggregation interval"),
    current_user: UserResponse = Depends(require_viewer_role),
    telemetry_service: TelemetryService = Depends(get_telemetry_service)
):
    """
    Get aggregated telemetry data for a specific field.

    Returns min, max, mean, and count statistics for the specified field and time range.
    User must have access to the organization containing the device.
    """
    try:
        # Validate time range
        if start_time >= end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start time must be before end time"
            )

        aggregated_telemetry = await telemetry_service.get_aggregated_telemetry(
            device_id=device_id,
            field=field,
            start_time=start_time,
            end_time=end_time,
            interval=interval
        )

        logger.info(f"Retrieved aggregated telemetry for device {device_id}, field {field.value}")
        return aggregated_telemetry

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting aggregated telemetry for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve aggregated telemetry"
        )


@router.get(
    "/summary/{device_id}",
    summary="Get telemetry summary",
    description="Get telemetry summary statistics for a device over a specified period."
)
async def get_telemetry_summary(
    device_id: UUID,
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back (max 7 days)"),
    current_user: UserResponse = Depends(require_viewer_role),
    telemetry_service: TelemetryService = Depends(get_telemetry_service)
):
    """
    Get telemetry summary for a device over specified hours.

    Returns summary statistics for all telemetry fields.
    User must have access to the organization containing the device.
    """
    try:
        summary = await telemetry_service.get_device_telemetry_summary(
            device_id=device_id,
            hours=hours
        )

        logger.info(f"Retrieved telemetry summary for device {device_id}")
        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting telemetry summary for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve telemetry summary"
        )


@router.get(
    "/stream",
    summary="Stream real-time telemetry data",
    description="Stream real-time telemetry data using Server-Sent Events (SSE)."
)
async def stream_telemetry(
    device_ids: Optional[List[UUID]] = Query(None, description="List of device IDs to stream (empty for all)"),
    fields: Optional[List[TelemetryField]] = Query(None, description="Telemetry fields to include in stream"),
    organization_id: Optional[UUID] = Query(None, description="Organization ID filter"),
    site_id: Optional[UUID] = Query(None, description="Site ID filter"),
    area_id: Optional[UUID] = Query(None, description="Area ID filter"),
    client_id: Optional[str] = Query(None, description="Client identifier for connection tracking"),
    current_user: UserResponse = Depends(require_viewer_role),
    streaming_service: StreamingService = Depends(get_streaming_service)
) -> StreamingResponse:
    """
    Stream real-time telemetry data using Server-Sent Events.

    Establishes a persistent connection for real-time telemetry updates.
    Supports filtering by device IDs, fields, and hierarchy levels.
    User must have access to the specified organization/hierarchy.
    """
    try:
        # TODO: Add proper hierarchy access validation
        # For now, we'll validate access in the streaming service

        stream_response = await streaming_service.create_telemetry_stream_response(
            device_ids=device_ids,
            fields=fields,
            organization_id=organization_id,
            site_id=site_id,
            area_id=area_id,
            client_id=client_id or f"user_{current_user.id}"
        )

        logger.info(f"Created telemetry stream for user {current_user.email}")
        return stream_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating telemetry stream: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create telemetry stream"
        )


@router.post(
    "/ingest/{device_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest telemetry data",
    description="Ingest telemetry data for a device. For internal/system use."
)
async def ingest_telemetry(
    device_id: UUID,
    readings: dict,
    timestamp: Optional[datetime] = None,
    current_user: UserResponse = Depends(require_viewer_role),
    telemetry_service: TelemetryService = Depends(get_telemetry_service)
):
    """
    Ingest telemetry data for a device.

    This endpoint is primarily for internal use or system integration.
    In production, telemetry data typically comes through MQTT.
    """
    try:
        # Validate readings format
        if not isinstance(readings, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Readings must be a dictionary of field names to numeric values"
            )

        # Validate readings contain numeric values
        for field_name, value in readings.items():
            if not isinstance(value, (int, float)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid value for field '{field_name}': must be numeric"
                )

        success = await telemetry_service.write_telemetry_reading(
            device_id=device_id,
            readings=readings,
            timestamp=timestamp
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to ingest telemetry data"
            )

        logger.info(f"Ingested telemetry data for device {device_id}")
        return {"message": "Telemetry data ingested successfully", "device_id": str(device_id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting telemetry for device {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to ingest telemetry data"
        )


@router.post(
    "/ingest/batch",
    status_code=status.HTTP_201_CREATED,
    summary="Batch ingest telemetry data",
    description="Ingest multiple telemetry readings in batch. For internal/system use."
)
async def batch_ingest_telemetry(
    readings_batch: List[dict],
    current_user: UserResponse = Depends(require_viewer_role),
    telemetry_service: TelemetryService = Depends(get_telemetry_service)
):
    """
    Batch ingest telemetry data for multiple devices.

    This endpoint is for bulk data ingestion or system integration.
    Each reading should contain device_id, fields (readings), and optional timestamp.
    """
    try:
        # Validate batch format
        if not isinstance(readings_batch, list) or len(readings_batch) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Readings batch must be a non-empty list"
            )

        if len(readings_batch) > 1000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Batch size cannot exceed 1000 readings"
            )

        # Validate each reading in batch
        for i, reading in enumerate(readings_batch):
            if not isinstance(reading, dict):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Reading at index {i} must be a dictionary"
                )

            if 'device_id' not in reading:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Reading at index {i} missing required 'device_id' field"
                )

            if 'fields' not in reading:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Reading at index {i} missing required 'fields' field"
                )

        written_count = await telemetry_service.write_telemetry_batch(readings_batch)

        logger.info(f"Batch ingested {written_count} telemetry readings")
        return {
            "message": f"Successfully ingested {written_count} telemetry readings",
            "ingested_count": written_count,
            "total_count": len(readings_batch)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch ingesting telemetry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to batch ingest telemetry data"
        )