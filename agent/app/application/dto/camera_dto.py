"""
Camera DTO
==========

Pydantic models for camera API requests and responses.
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class CameraCreateRequest(BaseModel):
    """DTO for creating/updating a camera. Field names match web backend."""
    id: str = Field(..., description="Unique camera identifier (matches web backend)")
    owner_user_id: str = Field(..., description="User ID who owns this camera (matches web backend)")
    name: str = Field(..., description="Camera name (matches web backend)")
    stream_url: str = Field(..., description="Stream URL (matches web backend)")
    device_id: Optional[str] = Field(None, description="Optional device identifier")
    
    class Config:
        schema_extra = {
            "example": {
                "id": "CAM-6CBFAA3D8AB5",
                "stream_url": "rtsp://algoorange:algoorange2025@192.168.1.6:554/stream1",
                "name": "samit_cam",
                "owner_user_id": "6928422b8c9933d948cfdc21",
                "device_id": "69465dc123d2a21e3847c065"
            }
        }


class CameraResponse(BaseModel):
    """DTO for camera data. Field names match web backend."""
    id: str
    owner_user_id: str
    name: str
    stream_url: str
    device_id: Optional[str] = None
    status: str  # Internal field (not in web backend)
    created_at: datetime  # Internal field (not in web backend)
    updated_at: datetime  # Internal field (not in web backend)
    
    class Config:
        schema_extra = {
            "example": {
                "id": "CAM-6CBFAA3D8AB5",
                "stream_url": "rtsp://algoorange:algoorange2025@192.168.1.6:554/stream1",
                "name": "samit_cam",
                "owner_user_id": "6928422b8c9933d948cfdc21",
                "device_id": "69465dc123d2a21e3847c065",
                "status": "active",
                "created_at": "2025-12-20T09:11:50.840Z",
                "updated_at": "2025-12-20T09:11:50.840Z"
            }
        }


class CameraDeleteResponse(BaseModel):
    """DTO for camera deletion."""
    status: str
    camera_id: str
    message: str


class WebRTCConfigResponse(BaseModel):
    """DTO for WebRTC configuration."""
    signaling_url: str = Field(..., description="WebSocket URL for WebRTC signaling")
    ice_servers: List[Dict[str, Any]] = Field(..., description="ICE servers for NAT traversal")
    camera_id: Optional[str] = Field(None, description="Camera ID (only for camera-specific config)")
    camera_name: Optional[str] = Field(None, description="Camera name (only for camera-specific config)")
    
    class Config:
        schema_extra = {
            "example": {
                "signaling_url": "ws://localhost:8765/viewer:6928422b8c9933d948cfdc21",
                "ice_servers": [
                    {"urls": "stun:stun.l.google.com:19302"}
                ]
            }
        }

