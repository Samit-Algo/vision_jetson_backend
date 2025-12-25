"""
Register Camera Use Case
========================

Business use case for registering a new camera or updating an existing one.
"""
from typing import Optional
from datetime import datetime

from app.domain.models.camera import Camera
from app.domain.repositories.camera_repository import CameraRepository


class RegisterCameraUseCase:
    """
    Use case for registering or updating a camera.
    
    This encapsulates the business logic for camera registration.
    """
    
    def __init__(self, camera_repository: CameraRepository):
        """
        Initialize use case with repository.
        
        Args:
            camera_repository: Repository for camera persistence
        """
        self._repository = camera_repository
    
    def execute(
        self,
        id: str,
        owner_user_id: str,
        name: str,
        stream_url: str,
        device_id: Optional[str] = None,
    ) -> Camera:
        """
        Execute the register camera use case.
        
        Args:
            id: Unique camera identifier (matches web backend field name)
            owner_user_id: User ID who owns the camera (matches web backend field name)
            name: Camera name (matches web backend field name)
            stream_url: Stream URL (matches web backend field name)
            device_id: Optional device identifier
            
        Returns:
            Registered camera entity
            
        Raises:
            ValueError: If input validation fails
        """
        # Validate inputs
        if not id or not id.strip():
            raise ValueError("Camera ID is required")
        if not stream_url or not stream_url.strip():
            raise ValueError("Stream URL is required")
        if not name or not name.strip():
            raise ValueError("Camera name is required")
        if not owner_user_id or not owner_user_id.strip():
            raise ValueError("Owner user ID is required")
        
        # Check if camera already exists
        existing_camera = self._repository.find_by_id(id)
        
        if existing_camera:
            # Update existing camera
            existing_camera.update_stream_url(stream_url)
            existing_camera.update_name(name)
            existing_camera.device_id = device_id
            existing_camera.activate()  # Ensure it's active
            return self._repository.update(existing_camera)
        else:
            # Create new camera
            new_camera = Camera(
                id=id.strip(),
                owner_user_id=owner_user_id.strip(),
                name=name.strip(),
                stream_url=stream_url.strip(),
                device_id=device_id,
                status="active",
            )
            return self._repository.create(new_camera)

