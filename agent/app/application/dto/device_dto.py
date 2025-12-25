"""
Device DTO
==========

Pydantic models for device API requests and responses.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DeviceCreateRequest(BaseModel):
    """DTO for creating/updating a device."""
    device_id: str = Field(..., description="Unique device identifier")
    web_backend_url: str = Field(..., description="Web backend URL for this device")
    user_id: str = Field(..., description="User ID who owns this device")
    name: Optional[str] = Field(None, description="Optional device name")
    
    class Config:
        schema_extra = {
            "example": {
                "device_id": "69465dc123d2a21e3847c065",
                "web_backend_url": "http://localhost:8000",
                "user_id": "6928422b8c9933d948cfdc21",
                "name": "Jetson Device 1"
            }
        }


class DeviceResponse(BaseModel):
    """DTO for device data."""
    device_id: str
    web_backend_url: str
    user_id: str
    name: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        schema_extra = {
            "example": {
                "device_id": "69465dc123d2a21e3847c065",
                "web_backend_url": "http://localhost:8000",
                "user_id": "6928422b8c9933d948cfdc21",
                "name": "Jetson Device 1",
                "status": "active",
                "created_at": "2025-12-20T09:11:50.840Z",
                "updated_at": "2025-12-20T09:11:50.840Z"
            }
        }

