"""
Camera Controller
=================

FastAPI controller for camera management endpoints.
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status, Depends

from app.application.dto.camera_dto import (
    CameraCreateRequest,
    CameraResponse,
    CameraDeleteResponse,
    WebRTCConfigResponse,
)
from app.api.v1.dependencies import get_camera_service
from app.application.services.camera_service import CameraService

router = APIRouter(tags=["cameras"])


@router.post(
    "/create",
    response_model=CameraResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register or update a camera",
    description="""
    Register a new camera or update an existing one.
    
    When a camera is registered:
    1. Camera config is saved to MongoDB 'cameras' collection
    2. Runner will automatically start CameraPublisher on next poll (every 5 seconds)
    3. CameraPublisher will begin streaming frames to shared_store
    """
)
async def create_camera(
    request: CameraCreateRequest,
    service: CameraService = Depends(get_camera_service),
) -> CameraResponse:
    """Register or update a camera."""
    try:
        camera = service.register_camera(
            id=request.id,
            owner_user_id=request.owner_user_id,
            name=request.name,
            stream_url=request.stream_url,
            device_id=request.device_id,
        )
        
        return CameraResponse(
            id=camera.id,
            owner_user_id=camera.owner_user_id,
            name=camera.name,
            stream_url=camera.stream_url,
            device_id=camera.device_id,
            status=camera.status,
            created_at=camera.created_at,
            updated_at=camera.updated_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/remove/{camera_id}",
    response_model=CameraDeleteResponse,
    summary="Remove a camera",
    description="""
    Remove a camera by setting its status to 'inactive'.
    
    Runner will automatically stop CameraPublisher on next poll.
    """
)
async def remove_camera(
    camera_id: str,
    service: CameraService = Depends(get_camera_service),
) -> CameraDeleteResponse:
    """Remove a camera."""
    try:
        success = service.remove_camera(camera_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Camera '{camera_id}' not found"
            )
        
        return CameraDeleteResponse(
            status="removed",
            camera_id=camera_id,
            message=f"Camera '{camera_id}' has been removed. CameraPublisher will stop on next poll."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/list",
    response_model=List[CameraResponse],
    summary="List cameras",
    description="Get list of all cameras, optionally filtered by owner_user_id or status."
)
async def list_cameras(
    owner_user_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    service: CameraService = Depends(get_camera_service),
) -> List[CameraResponse]:
    """List cameras with optional filters."""
    cameras = service.list_cameras(owner_user_id=owner_user_id, status=status_filter)
    
    return [
        CameraResponse(
            id=cam.id,
            owner_user_id=cam.owner_user_id,
            name=cam.name,
            stream_url=cam.stream_url,
            device_id=cam.device_id,
            status=cam.status,
            created_at=cam.created_at,
            updated_at=cam.updated_at,
        )
        for cam in cameras
    ]


@router.get(
    "/get/{camera_id}",
    response_model=CameraResponse,
    summary="Get camera by ID",
    description="Get details of a specific camera."
)
async def get_camera(
    camera_id: str,
    service: CameraService = Depends(get_camera_service),
) -> CameraResponse:
    """Get a specific camera by ID."""
    camera = service.get_camera(camera_id)
    
    if not camera:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Camera '{camera_id}' not found"
        )
    
    return CameraResponse(
        id=camera.id,
        owner_user_id=camera.owner_user_id,
        name=camera.name,
        stream_url=camera.stream_url,
        device_id=camera.device_id,
        status=camera.status,
        created_at=camera.created_at,
        updated_at=camera.updated_at,
    )


@router.get(
    "/webrtc-config",
    response_model=WebRTCConfigResponse,
    summary="Get WebRTC configuration",
    description="Get WebRTC configuration for frontend (signaling URL and ICE servers)."
)
async def get_webrtc_config(
    user_id: str,
    service: CameraService = Depends(get_camera_service),
) -> WebRTCConfigResponse:
    """Get WebRTC configuration for a user."""
    try:
        config = service.get_stream_config(user_id)
        return WebRTCConfigResponse(**config)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get(
    "/{camera_id}/stream-config",
    response_model=WebRTCConfigResponse,
    summary="Get camera stream configuration",
    description="Get WebRTC configuration for viewing a specific camera's live stream."
)
async def get_camera_stream_config(
    camera_id: str,
    user_id: str,
    service: CameraService = Depends(get_camera_service),
) -> WebRTCConfigResponse:
    """Get WebRTC configuration for a specific camera stream."""
    try:
        config = service.get_camera_stream_config(camera_id, user_id)
        return WebRTCConfigResponse(**config)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get camera stream config: {e}"
        )

