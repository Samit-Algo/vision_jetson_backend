"""
Camera Model
============

Domain model representing a camera in the system.
This is a pure domain object with no infrastructure dependencies.
"""
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field

from app.utils.datetime_utils import now


@dataclass
class Camera:
    """
    Camera domain model.
    
    Represents a camera in the system with all its business attributes.
    This model is independent of any persistence mechanism.
    
    Field names match web backend structure for consistency.
    """
    id: str  # Changed from camera_id to id (matches web backend)
    owner_user_id: str  # Changed from user_id to owner_user_id (matches web backend)
    name: str  # Changed from camera_name to name (matches web backend)
    stream_url: str  # Changed from rtsp_url to stream_url (matches web backend)
    device_id: Optional[str] = None
    status: str = "active"  # "active" | "inactive" (internal field, not in web backend)
    created_at: datetime = field(default_factory=lambda: now())  # Internal field
    updated_at: datetime = field(default_factory=lambda: now())  # Internal field
    
    def activate(self) -> None:
        """Activate the camera."""
        self.status = "active"
        self.updated_at = now()
    
    def deactivate(self) -> None:
        """Deactivate the camera."""
        self.status = "inactive"
        self.updated_at = now()
    
    def is_active(self) -> bool:
        """Check if camera is active."""
        return self.status == "active"
    
    def update_stream_url(self, new_url: str) -> None:
        """Update stream URL."""
        if not new_url or not new_url.strip():
            raise ValueError("Stream URL cannot be empty")
        self.stream_url = new_url.strip()
        self.updated_at = now()
    
    def update_name(self, new_name: str) -> None:
        """Update camera name."""
        if not new_name or not new_name.strip():
            raise ValueError("Camera name cannot be empty")
        self.name = new_name.strip()
        self.updated_at = now()
