"""
Device Routes
=============

FastAPI routes for device management endpoints.
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, Depends

from agent.api.schemas.device_schemas import (
    DeviceCreateRequest,
    DeviceResponse,
)
from agent.api.dependencies.container import get_device_service
from agent.application.services.device_service import DeviceService

router = APIRouter(prefix="/api", tags=["devices"])


@router.post(
    "/devices",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register or update a device",
    description="""
    Register a new device or update an existing one.
    
    When a device is registered:
    1. Device config is saved to MongoDB 'devices' collection
    2. Web backend URL is stored for this device
    3. Device can be used for camera and agent operations
    """
)
async def register_device(
    request: DeviceCreateRequest,
    service: DeviceService = Depends(get_device_service),
) -> DeviceResponse:
    """Register or update a device."""
    try:
        device = service.register_device(
            device_id=request.device_id,
            web_backend_url=request.web_backend_url,
            user_id=request.user_id,
            name=request.name,
        )
        
        return DeviceResponse(
            device_id=device.device_id,
            web_backend_url=device.web_backend_url,
            user_id=device.user_id,
            name=device.name,
            status=device.status,
            created_at=device.created_at,
            updated_at=device.updated_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/devices/{device_id}",
    response_model=DeviceResponse,
    summary="Get device by ID",
    description="Get details of a specific device."
)
async def get_device(
    device_id: str,
    service: DeviceService = Depends(get_device_service),
) -> DeviceResponse:
    """Get a specific device by ID."""
    device = service.get_device(device_id)
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found"
        )
    
    return DeviceResponse(
        device_id=device.device_id,
        web_backend_url=device.web_backend_url,
        user_id=device.user_id,
        name=device.name,
        status=device.status,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


@router.get(
    "/devices",
    response_model=List[DeviceResponse],
    summary="List devices",
    description="Get list of all devices, optionally filtered by user_id or status."
)
async def list_devices(
    user_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    service: DeviceService = Depends(get_device_service),
) -> List[DeviceResponse]:
    """List devices with optional filters."""
    devices = service.list_devices(user_id=user_id, status=status_filter)
    
    return [
        DeviceResponse(
            device_id=dev.device_id,
            web_backend_url=dev.web_backend_url,
            user_id=dev.user_id,
            name=dev.name,
            status=dev.status,
            created_at=dev.created_at,
            updated_at=dev.updated_at,
        )
        for dev in devices
    ]

