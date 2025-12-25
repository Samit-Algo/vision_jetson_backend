"""
Camera Service
==============

Application service that coordinates camera-related operations.
This service orchestrates multiple use cases.
"""
from typing import List, Optional

from app.domain.models.camera import Camera
from app.domain.repositories.camera_repository import CameraRepository
from app.application.use_cases.camera.register_camera import RegisterCameraUseCase
from app.application.use_cases.camera.remove_camera import RemoveCameraUseCase
from app.application.use_cases.camera.get_stream_config import GetStreamConfigUseCase
from app.application.use_cases.camera.get_camera_stream_config import GetCameraStreamConfigUseCase


class CameraService:
    """
    Application service for camera operations.
    
    This service coordinates multiple use cases and provides
    a high-level interface for camera management.
    """
    
    def __init__(self, camera_repository: CameraRepository):
        """
        Initialize service with repository.
        
        Args:
            camera_repository: Repository for camera persistence
        """
        self._repository = camera_repository
        self._register_use_case = RegisterCameraUseCase(camera_repository)
        self._remove_use_case = RemoveCameraUseCase(camera_repository)
        self._get_config_use_case = GetStreamConfigUseCase(camera_repository)
        self._get_camera_config_use_case = GetCameraStreamConfigUseCase(camera_repository)
    
    def register_camera(
        self,
        id: str,
        owner_user_id: str,
        name: str,
        stream_url: str,
        device_id: Optional[str] = None,
    ) -> Camera:
        """
        Register or update a camera.
        
        Args:
            id: Unique camera identifier (matches web backend field name)
            owner_user_id: User ID who owns the camera (matches web backend field name)
            name: Camera name (matches web backend field name)
            stream_url: Stream URL (matches web backend field name)
            device_id: Optional device identifier
            
        Returns:
            Registered camera entity
        """
        return self._register_use_case.execute(
            id=id,
            owner_user_id=owner_user_id,
            name=name,
            stream_url=stream_url,
            device_id=device_id,
        )
    
    def remove_camera(self, camera_id: str) -> bool:
        """
        Remove (deactivate) a camera.
        
        Args:
            camera_id: Unique camera identifier
            
        Returns:
            True if camera was found and removed, False otherwise
        """
        return self._remove_use_case.execute(camera_id)
    
    def get_camera(self, camera_id: str) -> Optional[Camera]:
        """
        Get a camera by ID.
        
        Args:
            camera_id: Unique camera identifier
            
        Returns:
            Camera entity if found, None otherwise
        """
        return self._repository.find_by_id(camera_id)
    
    def list_cameras(
        self,
        owner_user_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Camera]:
        """
        List cameras with optional filters.
        
        Args:
            owner_user_id: Filter by owner user ID (matches web backend field name)
            status: Filter by status ('active' or 'inactive')
            
        Returns:
            List of camera entities
        """
        if owner_user_id:
            cameras = self._repository.find_by_user_id(owner_user_id)
        else:
            cameras = self._repository.find_all_active()
        
        if status:
            cameras = [cam for cam in cameras if cam.status == status]
        
        return cameras
    
    def get_stream_config(self, user_id: str) -> dict:
        """
        Get WebRTC stream configuration for a user.
        
        Args:
            user_id: User ID requesting the configuration
            
        Returns:
            Dictionary with signaling_url and ice_servers
        """
        return self._get_config_use_case.execute(user_id)
    
    def get_camera_stream_config(self, camera_id: str, user_id: str) -> dict:
        """
        Get WebRTC stream configuration for a specific camera.
        
        Args:
            camera_id: Camera identifier
            user_id: User ID (for validation)
            
        Returns:
            Dictionary with signaling_url, ice_servers, camera_id, and camera_name
        """
        return self._get_camera_config_use_case.execute(camera_id, user_id)

