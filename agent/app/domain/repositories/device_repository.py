"""
Device Repository Interface
===========================

Abstract interface for device data access.
Implementations should be in the infrastructure layer.
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from app.domain.models.device import Device


class DeviceRepository(ABC):
    """
    Abstract repository for device persistence operations.
    
    This interface defines the contract for device data access.
    Concrete implementations should be in the infrastructure layer.
    """
    
    @abstractmethod
    def create(self, device: Device) -> Device:
        """
        Create a new device.
        
        Args:
            device: Device entity to create
            
        Returns:
            Created device entity
        """
        pass
    
    @abstractmethod
    def update(self, device: Device) -> Device:
        """
        Update an existing device.
        
        Args:
            device: Device entity with updated data
            
        Returns:
            Updated device entity
        """
        pass
    
    @abstractmethod
    def find_by_id(self, device_id: str) -> Optional[Device]:
        """
        Find a device by its ID.
        
        Args:
            device_id: Unique device identifier
            
        Returns:
            Device entity if found, None otherwise
        """
        pass
    
    @abstractmethod
    def find_by_user_id(self, user_id: str) -> List[Device]:
        """
        Find all devices for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of device entities
        """
        pass
    
    @abstractmethod
    def find_all_active(self) -> List[Device]:
        """
        Find all active devices.
        
        Returns:
            List of active device entities
        """
        pass
    
    @abstractmethod
    def delete(self, device_id: str) -> bool:
        """
        Delete (deactivate) a device.
        
        Args:
            device_id: Unique device identifier
            
        Returns:
            True if device was found and deleted, False otherwise
        """
        pass
    
    @abstractmethod
    def exists(self, device_id: str) -> bool:
        """
        Check if a device exists.
        
        Args:
            device_id: Unique device identifier
            
        Returns:
            True if device exists, False otherwise
        """
        pass

