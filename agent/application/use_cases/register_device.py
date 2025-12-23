"""
Register Device Use Case
========================

Business use case for registering a new device or updating an existing one.
"""
from typing import Optional
from datetime import datetime

from agent.domain.entities.device import Device
from agent.domain.repositories.device_repository import DeviceRepository


class RegisterDeviceUseCase:
    """
    Use case for registering or updating a device.
    
    This encapsulates the business logic for device registration.
    """
    
    def __init__(self, device_repository: DeviceRepository):
        """
        Initialize use case with repository.
        
        Args:
            device_repository: Repository for device persistence
        """
        self._repository = device_repository
    
    def execute(
        self,
        device_id: str,
        web_backend_url: str,
        user_id: str,
        name: Optional[str] = None,
    ) -> Device:
        """
        Execute the register device use case.
        
        Args:
            device_id: Unique device identifier
            web_backend_url: Web backend URL for this device
            user_id: User ID who owns the device
            name: Optional device name
            
        Returns:
            Registered device entity
            
        Raises:
            ValueError: If input validation fails
        """
        # Validate inputs
        if not device_id or not device_id.strip():
            raise ValueError("Device ID is required")
        if not web_backend_url or not web_backend_url.strip():
            raise ValueError("Web backend URL is required")
        if not user_id or not user_id.strip():
            raise ValueError("User ID is required")
        
        # Check if device already exists
        existing_device = self._repository.find_by_id(device_id)
        
        if existing_device:
            # Update existing device
            existing_device.update_web_backend_url(web_backend_url)
            if name:
                existing_device.update_name(name)
            existing_device.activate()  # Ensure it's active
            return self._repository.update(existing_device)
        else:
            # Create new device
            new_device = Device(
                device_id=device_id.strip(),
                web_backend_url=web_backend_url.strip(),
                user_id=user_id.strip(),
                name=name.strip() if name else None,
                status="active",
            )
            return self._repository.create(new_device)

