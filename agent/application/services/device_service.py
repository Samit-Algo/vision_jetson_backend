"""
Device Service
==============

Application service that coordinates device-related operations.
This service orchestrates multiple use cases.
"""
from typing import List, Optional

from agent.domain.entities.device import Device
from agent.domain.repositories.device_repository import DeviceRepository
from agent.application.use_cases.register_device import RegisterDeviceUseCase


class DeviceService:
    """
    Application service for device operations.
    
    This service coordinates multiple use cases and provides
    a high-level interface for device management.
    """
    
    def __init__(self, device_repository: DeviceRepository):
        """
        Initialize service with repository.
        
        Args:
            device_repository: Repository for device persistence
        """
        self._repository = device_repository
        self._register_use_case = RegisterDeviceUseCase(device_repository)
    
    def register_device(
        self,
        device_id: str,
        web_backend_url: str,
        user_id: str,
        name: Optional[str] = None,
    ) -> Device:
        """
        Register or update a device.
        
        Args:
            device_id: Unique device identifier
            web_backend_url: Web backend URL for this device
            user_id: User ID who owns the device
            name: Optional device name
            
        Returns:
            Registered device entity
        """
        return self._register_use_case.execute(
            device_id=device_id,
            web_backend_url=web_backend_url,
            user_id=user_id,
            name=name,
        )
    
    def get_device(self, device_id: str) -> Optional[Device]:
        """
        Get a device by ID.
        
        Args:
            device_id: Unique device identifier
            
        Returns:
            Device entity if found, None otherwise
        """
        return self._repository.find_by_id(device_id)
    
    def list_devices(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Device]:
        """
        List devices with optional filters.
        
        Args:
            user_id: Filter by user ID
            status: Filter by status ('active' or 'inactive')
            
        Returns:
            List of device entities
        """
        if user_id:
            devices = self._repository.find_by_user_id(user_id)
        else:
            devices = self._repository.find_all_active()
        
        if status:
            devices = [dev for dev in devices if dev.status == status]
        
        return devices

