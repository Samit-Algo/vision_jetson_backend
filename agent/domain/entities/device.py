"""
Device Entity
=============

Domain entity representing a device in the system.
This is a pure domain object with no infrastructure dependencies.
"""
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Device:
    """
    Device domain entity.
    
    Represents a device in the system with web backend connection information.
    This entity is independent of any persistence mechanism.
    """
    device_id: str
    web_backend_url: str
    user_id: str
    name: Optional[str] = None
    status: str = "active"  # "active" | "inactive"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def activate(self) -> None:
        """Activate the device."""
        self.status = "active"
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Deactivate the device."""
        self.status = "inactive"
        self.updated_at = datetime.utcnow()
    
    def is_active(self) -> bool:
        """Check if device is active."""
        return self.status == "active"
    
    def update_web_backend_url(self, new_url: str) -> None:
        """Update web backend URL."""
        if not new_url or not new_url.strip():
            raise ValueError("Web backend URL cannot be empty")
        self.web_backend_url = new_url.strip()
        self.updated_at = datetime.utcnow()
    
    def update_name(self, new_name: str) -> None:
        """Update device name."""
        if new_name:
            self.name = new_name.strip()
            self.updated_at = datetime.utcnow()

